#!/usr/bin/env python3
"""
generate_dataset.py  -  DineIQ Analytics synthetic restaurant dataset (Phase 1)

HOW THE GENERATOR THINKS (read this before you read the code)
-------------------------------------------------------------
1. Static tables first: categories, menu items, restaurants, price history,
   promotions, customers.
2. Demand model: for every (day, location, hour-group, promotion) the
   probability of picking a menu item is
        popularity x season x weekend x price effect x location affinity
        x hour-of-day effect x promotion boost x basket pairing
   Everything that makes the data "realistic" is one of those multipliers.
3. Orders are created for every customer according to their hidden behaviour
   type (loyal, promo-driven, churned, ...), then order lines are sampled in
   CHUNKS so memory stays small and the files are written as part-files.
4. Operational tables (ratings, wastage, inventory) are derived from the
   simulated sales so that they are consistent with the orders.
5. Finally, controlled DIRT is injected (duplicates, invalid values ...).
   Every injection is counted in raw_data/_ground_truth/injection_log.json
   so you can later prove your data-quality step finds them.

Run:   python generate_dataset.py --out ..            (full size, ~1.1M order lines)
       python generate_dataset.py --out /tmp/t --scale 0.05      (quick smoke test)
"""
import argparse
import json
import os
import shutil
import time

import numpy as np
import pandas as pd

import config as C

T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def ids(prefix, arr, width):
    """Vectorised id formatter:  ids('ORD', [1,2], 8) -> ['ORD00000001','ORD00000002']"""
    return np.char.add(prefix, np.char.zfill(np.asarray(arr).astype(str), width))


# ============================================================================
# 1. STATIC TABLES
# ============================================================================
def build_categories():
    return pd.DataFrame(
        [(c[0], c[1], c[2], c[3]) for c in C.CATEGORIES],
        columns=["category_id", "category_name", "perishability", "meal_period"])


def build_menu(rng, start):
    """Menu items + per-item numeric arrays used by the demand model."""
    arch_of = {n: a for a, names in C.ARCHETYPE.items() for n in names}
    cat_row = {c[0]: c for c in C.CATEGORIES}
    cat_ids = [c[0] for c in C.CATEGORIES]
    weight_ranges = {"C01": (150, 300), "C02": (300, 450), "C03": (300, 450), "C04": (250, 450),
                     "C05": (250, 400), "C06": (350, 600), "C07": (100, 250), "C08": (120, 250),
                     "C09": (330, 500), "C10": (200, 300), "C11": (150, 250), "C12": (250, 400)}

    def day_idx(s):
        return (pd.Timestamp(s) - start).days

    rows, tags = [], []
    n = 0
    for cid in cat_ids:
        for name, price in C.CATALOG[cid]:
            n += 1
            arch = arch_of.get(name, "BASE")
            pop = rng.lognormal(0, 0.45) * C.POP_FACTOR[arch]
            if name in C.PROMO_DEPENDENT: pop *= 0.25
            if name in C.PRICE_SENSITIVE: pop *= 1.6
            if name in C.WEEKEND_ITEMS: pop *= 1.1
            lo, hi = C.COST_RATIO.get(arch, (None, None))
            ratio = rng.uniform(lo, hi) if lo is not None else cat_row[cid][4] * rng.uniform(0.9, 1.15)
            cost = round(price * ratio / 10) * 10
            if arch == "WASTE_HEAVY":
                over = 0.22 * rng.uniform(0.9, 1.2)
            else:
                over = cat_row[cid][7] * rng.uniform(0.7, 1.3)
            quality = C.QUALITY_OVERRIDE.get(name, C.QUALITY[arch]) + rng.normal(0, 0.12)
            elastic = -0.4 + rng.normal(0, 0.1)
            if name in C.PRICE_SENSITIVE: elastic = -2.4
            if name in C.LOW_SENSITIVITY: elastic = -0.1
            # availability window (day index; +-big = always)
            a_from, a_to = -9999, 9999
            launch = pd.Timestamp("2022-01-01") + pd.Timedelta(days=int(rng.integers(0, 1350)))
            av_from_s = av_to_s = None
            if name in C.NEW_ITEMS:
                a_from = day_idx(C.NEW_ITEMS[name]); launch = pd.Timestamp(C.NEW_ITEMS[name]); av_from_s = C.NEW_ITEMS[name]
            if name in C.MID_LAUNCH:
                a_from = day_idx(C.MID_LAUNCH[name]); launch = pd.Timestamp(C.MID_LAUNCH[name]); av_from_s = C.MID_LAUNCH[name]
            if name in C.LIMITED_WINDOWS:
                av_from_s, av_to_s = C.LIMITED_WINDOWS[name]
                a_from, a_to = day_idx(av_from_s), day_idx(av_to_s)
            if name in C.DISCONTINUED:
                av_to_s = C.DISCONTINUED[name]; a_to = day_idx(av_to_s)
            season = "NONE"
            if name in C.COLD_WEATHER_ITEMS: season = "COLD_WEATHER"
            if name in C.HOT_WEATHER_ITEMS: season = "HOT_WEATHER"
            if name in C.LIMITED_WINDOWS: season = "LIMITED_TIME"
            desc = f"{name} - {cat_row[cid][1].lower()} signature"
            rows.append(dict(
                item_id=f"M{n:03d}", item_name=name, category_id=cid,
                description=None if rng.random() < 0.03 else desc,
                base_price=float(price), base_cost=float(cost),
                portion_weight_g=int(rng.integers(*weight_ranges[cid])),
                prep_time_min=int(rng.integers(3, 35)),
                is_vegetarian=name in C.VEGETARIAN,
                launch_date=launch.strftime("%Y-%m-%d"),
                available_from=av_from_s, available_to=av_to_s,
                is_active=name not in C.DISCONTINUED,
                season_tag=season))
            tags.append(dict(item_id=f"M{n:03d}", item_name=name, archetype=arch,
                             price_sensitive=name in C.PRICE_SENSITIVE,
                             low_price_sensitivity=name in C.LOW_SENSITIVITY,
                             promo_dependent=name in C.PROMO_DEPENDENT,
                             weekend_item=name in C.WEEKEND_ITEMS,
                             seasonal=season, new_item=name in C.NEW_ITEMS,
                             discontinued=name in C.DISCONTINUED,
                             planted_location_effect=name in C.PLANTED_LOC))
            rows[-1]["_pop"] = pop; rows[-1]["_over"] = over; rows[-1]["_q"] = quality
            rows[-1]["_el"] = elastic; rows[-1]["_from"] = a_from; rows[-1]["_to"] = a_to
    df = pd.DataFrame(rows)
    arr = {k: df.pop(k).values for k in ["_pop", "_over", "_q", "_el", "_from", "_to"]}
    return df, arr, pd.DataFrame(tags)


def build_price_history(rng, menu, n_days, start):
    """One row per price/cost period + daily lookup matrices PRICE[d,i], COST[d,i]."""
    N = len(menu)
    PRICE = np.zeros((n_days, N), np.float32)
    COST = np.zeros((n_days, N), np.float32)
    rows = []
    pid = 0
    for i, r in menu.iterrows():
        name = r.item_name
        events = {}                                       # day -> [price_pct, cost_pct]
        if name in C.PRICE_SHOCKS:
            for d, p in C.PRICE_SHOCKS[name]:
                cp = 0.0 if name in C.COST_SHOCKS else p * rng.uniform(0.9, 1.1)
                events[d] = [p, cp]
        elif name not in C.COST_SHOCKS:
            for d in sorted(set(rng.integers(25, 335, rng.choice([0, 1, 1, 2, 2, 3])).tolist())):
                p = rng.uniform(0.05, 0.12)
                events[int(d)] = [p, p * rng.uniform(0.9, 1.1)]
        for d, p in C.COST_SHOCKS.get(name, []):
            events.setdefault(d, [0.0, 0.0])[1] += p
        price, cost = r.base_price, r.base_cost
        days = sorted(events)
        bounds = [0] + days + [n_days]
        eff0 = pd.Timestamp(r.available_from) if (r.available_from and pd.Timestamp(r.available_from) > start) \
            else pd.Timestamp("2025-01-01")
        for k in range(len(bounds) - 1):
            if k > 0:
                pp, cp = events[bounds[k]]
                price = round(price * (1 + pp) / 50) * 50
                cost = round(cost * (1 + cp) / 10) * 10
            PRICE[bounds[k]:bounds[k + 1], i] = price
            COST[bounds[k]:bounds[k + 1], i] = cost
            pid += 1
            if k == 0:
                reason = "INITIAL"
            else:
                pp, cp = events[bounds[k]]
                reason = ("PRICE_AND_COST_INCREASE" if pp > 0 and cp > 0
                          else "PRICE_INCREASE" if pp > 0 else "COST_INCREASE")
            frm = eff0 if k == 0 else start + pd.Timedelta(days=bounds[k])
            to = None if k == len(bounds) - 2 else (start + pd.Timedelta(days=bounds[k + 1] - 1)).strftime("%Y-%m-%d")
            rows.append(dict(price_id=f"PR{pid:05d}", item_id=r.item_id,
                             effective_from=frm.strftime("%Y-%m-%d"), effective_to=to,
                             price=float(price), unit_cost=float(cost), change_reason=reason))
    return pd.DataFrame(rows), PRICE, COST


def build_locations():
    return pd.DataFrame(
        [dict(location_id=l[0], restaurant_name=f"DineIQ {l[1]}", area=l[1], city=l[2], state=l[3],
              region=l[4], opening_date=l[6], seating_capacity=l[7], size_tier=l[8]) for l in C.LOCATIONS])


def build_promotions(menu, dates):
    """Promotion tables + arrays that drive the demand model."""
    D, N = len(dates), len(menu)
    P = len(C.PROMOS)
    cat_of = menu.category_id.values
    PB = np.ones((P + 1, N), np.float32)          # demand boost per promo (row 0 = no promo)
    ELIG = np.zeros((P + 1, N), bool)             # items that receive the discount
    PCT = np.zeros(P + 1, np.float32)
    ACT = np.zeros((P, D), bool)                  # promo active on day d
    LIFT = np.zeros(D)                            # extra overall traffic
    BROAD = np.zeros(D, bool)                     # big public promos (promo-driven customers react)
    CHF = np.ones((D, 4))                         # channel shift caused by promos
    OVER = np.ones((D, N), np.float32)            # wastage over-preparation multiplier
    CH_OK = np.ones((P + 1, 4), bool)
    ptype = [""]
    rows, items_rows = [], []
    dow_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    last_big_end = []
    for p, pr in enumerate(C.PROMOS, start=1):
        d0 = (pd.Timestamp(pr["start"]) - dates[0]).days
        d1 = (pd.Timestamp(pr["end"]) - dates[0]).days
        mask = np.zeros(D, bool); mask[max(d0, 0):d1 + 1] = True
        if pr["days"] is not None:
            mask &= np.isin(dates.dayofweek.values, pr["days"])
        ACT[p - 1] = mask
        scope = pr["scope"]
        if scope == "all": in_scope = np.ones(N, bool)
        else: in_scope = np.isin(cat_of, scope)
        ELIG[p] = in_scope if pr["pct"] > 0 else False
        PCT[p] = pr["pct"]
        PB[p, in_scope] = pr["boost"]
        PB[p, in_scope & np.isin(menu.item_name.values, C.PROMO_DEPENDENT)] *= C.PROMO_DEPENDENT_EXTRA
        for c, f in pr.get("cannibal", {}).items():
            PB[p, cat_of == c] *= f
        LIFT += mask * pr["lift"]
        if pr["broad"]: BROAD |= mask
        for ch, f in pr.get("chf", {}).items():
            CHF[mask, C.CHANNELS.index(ch)] *= f
        for c, f in pr.get("over", {}).items():
            OVER[np.ix_(mask, cat_of == c)] *= f
        if pr["channels"]:
            CH_OK[p] = [c in pr["channels"] for c in C.CHANNELS]
        ptype.append(pr["type"])
        if pr["lift"] >= 0.2: last_big_end.append(d1)
        days_txt = None if pr["days"] is None else ",".join(dow_names[x] for x in pr["days"])
        seg = "NEW_CUSTOMERS" if pr["new_only"] else "LOYALTY_MEMBERS" if pr["loyal_only"] else "ALL"
        rows.append(dict(promo_id=pr["id"], promo_name=pr["name"], promo_type=pr["type"],
                         discount_pct=pr["pct"], start_date=pr["start"], end_date=pr["end"],
                         applicable_days=days_txt,
                         channel_restriction=",".join(pr["channels"]) if pr["channels"] else None,
                         target_segment=seg, promo_code=pr["code"]))
        for i in np.where(in_scope)[0]:
            if pr["type"] != "FREE_DELIVERY":
                items_rows.append((pr["id"], menu.item_id.values[i]))
    DIP = np.ones(D)
    for e in last_big_end:
        DIP[e + 1:e + 1 + C.POST_PROMO_DIP_DAYS] = C.POST_PROMO_DIP
    promos = pd.DataFrame(rows)
    promo_items = pd.DataFrame(items_rows, columns=["promo_id", "item_id"])
    truth = pd.DataFrame([dict(promo_id=p["id"], promo_name=p["name"], planted_truth=p["tag"]) for p in C.PROMOS])
    return dict(promos=promos, promo_items=promo_items, truth=truth, PB=PB, ELIG=ELIG, PCT=PCT, ACT=ACT,
                LIFT=LIFT, BROAD=BROAD, CHF=CHF, OVER=OVER, CH_OK=CH_OK, DIP=DIP, ptype=ptype)


# ============================================================================
# 2. DEMAND MODEL MATRICES
# ============================================================================
def build_demand_matrices(rng, menu, arr, locs, dates, PRICE):
    D, N, L = len(dates), len(menu), len(locs)
    cat_ids = [c[0] for c in C.CATEGORIES]
    cat_of = menu.category_id.values
    cat_idx = np.array([cat_ids.index(c) for c in cat_of])
    names = menu.item_name.values
    month = dates.month.values
    dow = dates.dayofweek.values
    d_arr = np.arange(D)

    # availability (launch / limited window / discontinued)
    avail = (d_arr[:, None] >= arr["_from"][None, :]) & (d_arr[:, None] <= arr["_to"][None, :])
    # season profiles
    season = np.ones((D, N), np.float32)
    for nm in C.COLD_WEATHER_ITEMS:
        season[:, names == nm] = np.array(C.SEASON_PROFILE["COLD_WEATHER"])[month - 1][:, None]
    for nm in C.HOT_WEATHER_ITEMS:
        season[:, names == nm] = np.array(C.SEASON_PROFILE["HOT_WEATHER"])[month - 1][:, None]
    # weekend-only items
    wk = np.ones((D, N), np.float32)
    for nm in C.WEEKEND_ITEMS:
        wk[:, names == nm] = np.where(dow >= 5, 3.2, 0.35)[:, None]
    # new-item ramp-up (insufficient history, grows over 30 days)
    ramp = np.ones((D, N), np.float32)
    for i in range(N):
        f = arr["_from"][i]
        if f > 0:
            ramp[:, i] = np.clip(0.35 + 0.65 * (d_arr - f) / 30.0, 0.35, 1.0)
    # viral spike
    viral = np.ones((D, N), np.float32)
    for nm, (s, e, m) in C.VIRAL.items():
        i = np.where(names == nm)[0][0]
        d0 = (pd.Timestamp(s) - dates[0]).days; d1 = (pd.Timestamp(e) - dates[0]).days
        viral[d0:d1 + 1, i] = m
        viral[d1 + 1:, i] = 1.5
    # price effect: item price relative to its category's price index (isolates planted shocks)
    rel_price = PRICE / PRICE[0:1, :]
    cat_mean = np.zeros((D, len(cat_ids)), np.float32)
    for c in range(len(cat_ids)):
        cat_mean[:, c] = rel_price[:, cat_idx == c].mean(axis=1)
    rel = rel_price / cat_mean[:, cat_idx]
    price_mult = np.power(rel, arr["_el"][None, :]).astype(np.float32)
    DAYITEM = avail * season * wk * ramp * viral * price_mult

    # location x item affinity
    loc_ids = [l[0] for l in C.LOCATIONS]
    LOCAFF = rng.lognormal(0, 0.25, (L, N)).astype(np.float32)
    LOCAFF *= rng.lognormal(0, 0.20, (L, len(cat_ids)))[:, cat_idx].astype(np.float32)
    for nm, d in C.PLANTED_LOC.items():
        i = np.where(names == nm)[0][0]
        for l, lid in enumerate(loc_ids):
            LOCAFF[l, i] = LOCAFF[l, i] * d.get(lid, d.get("default", 1.0))

    # hour-group effect by category
    HOURM = np.ones((4, N), np.float32)
    for cid, mult in C.HOURGROUP_MULT.items():
        HOURM[:, cat_of == cid] = np.array(mult, np.float32)[:, None]

    # slot weights (first item vs add-on item) and pair affinities
    slot0 = np.array([C.CATEGORIES[c][5] for c in cat_idx], np.float32)
    slotN = np.array([C.CATEGORIES[c][6] for c in cat_idx], np.float32)
    PAIR = np.ones((N, N), np.float32)
    for a, b, m in C.PAIRS:
        ia, ib = np.where(names == a)[0][0], np.where(names == b)[0][0]
        PAIR[ia, ib] = m; PAIR[ib, ia] = m
    return dict(DAYITEM=DAYITEM.astype(np.float32), LOCAFF=LOCAFF, HOURM=HOURM, slot0=slot0, slotN=slotN,
                PAIR=PAIR, avail=avail, cat_idx=cat_idx)


def build_day_weights(dates, promo):
    D = len(dates)
    dow = dates.dayofweek.values; month = dates.month.values
    hol = np.ones(D)
    for s, m in C.HOLIDAYS.items():
        d = (pd.Timestamp(s) - dates[0]).days
        if 0 <= d < D: hol[d] = m
    base = (np.array(C.DOW_MULT)[dow] * np.array(C.MONTH_MULT)[month - 1]
            * (1 + C.GROWTH * np.arange(D) / (D - 1)) * hol)
    w_all = base * (1 + promo["LIFT"]) * np.where(promo["DIP"] < 1, 0.93, 1.0)
    # promo-driven customers: buy mostly while a big promotion is running, then go quiet
    w_promo = base * (C.PROMO_CUSTOMER_BASE + C.PROMO_CUSTOMER_RESPONSE * promo["BROAD"]) * promo["DIP"]
    # at-risk customers: activity fades through the year
    ramp = 1.0 - 0.9 * (np.arange(D) / (D - 1)) ** 1.2
    w_risk = w_all * ramp
    cum = lambda w: np.concatenate([[0.0], np.cumsum(w)])
    return cum(w_all), cum(w_promo), cum(w_risk)


# ============================================================================
# 3. CUSTOMERS
# ============================================================================
def build_customers(rng, n, locs, dates):
    L = len(locs)
    arch = rng.choice(len(C.ARCHETYPES), n, p=C.ARCH_SHARE)
    join = -rng.integers(30, 900, n)                              # negative = joined before the period
    occ = arch == 3
    in_year = occ & (rng.random(n) < 0.30)
    join[in_year] = rng.integers(0, 360, in_year.sum())
    new = arch == 4
    join[new] = rng.integers(265, 362, new.sum())
    tw = np.array([l[5] for l in C.LOCATIONS], float)
    open_idx = np.array([(pd.Timestamp(l[6]) - dates[0]).days for l in C.LOCATIONS])
    home = rng.choice(L - 1, n, p=tw[:-1] / tw[:-1].sum())          # last location = the new one
    cand = np.where((arch == 3) | (arch == 4))[0]
    sel = rng.choice(cand, int(0.018 * n), replace=False)             # customers living near the new location
    open24 = open_idx[-1]
    join[sel] = np.where(arch[sel] == 4, join[sel], rng.integers(open24, 360, len(sel)))
    home[sel] = L - 1
    a = np.maximum(join, 0)
    b = np.full(n, len(dates) - 1)
    ch = arch == 5
    b[ch] = rng.integers(60, 230, ch.sum())
    span = (b - a + 1) / 365.0
    mean = np.array(C.ARCH_MEAN_ORDERS)[arch]
    lam = rng.gamma(4.0, mean / 4.0)
    n_ord = rng.poisson(lam * span)
    n_ord = np.where(arch == 6, rng.poisson(lam), n_ord)
    n_ord = np.where(arch == 4, rng.poisson(np.maximum(lam - 1, 0.5)) + 1, n_ord)
    n_ord = np.maximum(n_ord, np.where(arch == 5, 2, 1))
    loyal_member = ((arch == 0) & (rng.random(n) < 0.95)) | (rng.random(n) < 0.10)
    pref = np.array([rng.choice(4, p=C.CHANNEL_P[x]) for x in range(8)])  # placeholder to keep rng order stable
    pref_ch = np.empty(n, int)
    for x in range(7):
        m = arch == x
        pref_ch[m] = rng.choice(4, m.sum(), p=C.CHANNEL_P[x])
    age = rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"], n, p=[0.18, 0.37, 0.25, 0.13, 0.07]).astype(object)
    age[rng.random(n) < C.DIRTY["customer_age_null"]] = None
    src = rng.choice(["ORGANIC", "PROMOTION", "REFERRAL", "SOCIAL_MEDIA", "WALK_IN"], n,
                     p=[0.25, 0.20, 0.15, 0.20, 0.20]).astype(object)
    pm = arch == 2
    src[pm] = rng.choice(["PROMOTION", "SOCIAL_MEDIA", "ORGANIC"], pm.sum(), p=[0.6, 0.25, 0.15])
    cities = np.array([l[2] for l in C.LOCATIONS])
    cust = pd.DataFrame(dict(
        customer_id=ids("CU", np.arange(1, n + 1), 6),
        signup_date=(dates[0] + pd.to_timedelta(join, unit="D")).strftime("%Y-%m-%d"),
        age_band=age, home_location_id=[C.LOCATIONS[h][0] for h in home], city=cities[home],
        preferred_channel=[C.CHANNELS[c] for c in pref_ch],
        acquisition_source=src, marketing_opt_in=rng.random(n) < 0.6,
        loyalty_member=loyal_member))
    truth = pd.DataFrame(dict(customer_id=cust.customer_id, planted_segment=[C.ARCHETYPES[x] for x in arch]))
    return cust, truth, dict(arch=arch, join=join, a=a, b=b, n_ord=n_ord, home=home,
                             loyal=loyal_member, open_idx=open_idx, tw=tw)


# ============================================================================
# 4. ORDER HEADERS (who, when, where, how) - lines come later, chunk by chunk
# ============================================================================
def build_order_headers(rng, cu, locs, dates, cums, promo, scale):
    D, L = len(dates), len(locs)
    n = len(cu["arch"])
    cum_all, cum_promo, cum_risk = cums
    rep = np.repeat(np.arange(n), cu["n_ord"])
    aa, bb = cu["a"][rep], cu["b"][rep]
    grp = np.where(cu["arch"][rep] == 2, 1, np.where(cu["arch"][rep] == 6, 2, 0))
    day = np.zeros(len(rep), int)
    for g, cum in enumerate((cum_all, cum_promo, cum_risk)):
        m = grp == g
        lo, hi = cum[aa[m]], cum[bb[m] + 1]
        u = lo + rng.random(m.sum()) * (hi - lo)
        day[m] = np.searchsorted(cum, u, side="right") - 1
    day = np.clip(day, aa, bb)
    cust = rep.astype(np.int64)
    n_reg = len(rep)

    # guest orders (no customer id)
    n_guest = int(n_reg * C.GUEST_SHARE / (1 - C.GUEST_SHARE))
    u = rng.random(n_guest) * cum_all[-1]
    gday = np.clip(np.searchsorted(cum_all, u, side="right") - 1, 0, D - 1)
    day = np.concatenate([day, gday]); cust = np.concatenate([cust, -np.ones(n_guest, np.int64)])
    kind = np.zeros(len(day), np.int8)
    forced = -np.ones(len(day), np.int64)
    loc_ids = [l[0] for l in C.LOCATIONS]

    # planted anomaly 1: one-day event spike at one location (extra guest orders)
    sp_loc, sp_date, sp_n = C.SPIKE_EVENT
    sp_n = max(20, int(sp_n * scale))
    sp_day = (pd.Timestamp(sp_date) - dates[0]).days
    day = np.concatenate([day, np.full(sp_n, sp_day)]); cust = np.concatenate([cust, -np.ones(sp_n, np.int64)])
    kind = np.concatenate([kind, np.full(sp_n, 1, np.int8)])
    forced = np.concatenate([forced, np.full(sp_n, loc_ids.index(sp_loc))])
    # planted anomaly 2: corporate catering orders with abnormally high order values
    n_cat = max(5, int(C.N_CATERING_ORDERS * scale))
    wk_days = np.where(dates.dayofweek.values < 5)[0]
    reg_good = np.where(cu["arch"] <= 1)[0]
    day = np.concatenate([day, rng.choice(wk_days, n_cat)])
    cust = np.concatenate([cust, rng.choice(reg_good, n_cat)])
    kind = np.concatenate([kind, np.full(n_cat, 2, np.int8)])
    forced = np.concatenate([forced, rng.choice([loc_ids.index(x) for x in C.CATERING_LOCS], n_cat)])
    m = len(day)

    # location: home restaurant 72% of the time, otherwise any (traffic weighted)
    tw = cu["tw"]
    loc = rng.choice(L, m, p=tw / tw.sum())
    use_home = (cust >= 0) & (rng.random(m) < 0.72)
    loc = np.where(use_home, cu["home"][np.maximum(cust, 0)], loc)
    loc = np.where(forced >= 0, forced, loc)
    bad = (cu["open_idx"][loc] > day) & (forced < 0)                  # not open yet -> another restaurant
    loc[bad] = rng.choice(L - 1, bad.sum(), p=tw[:-1] / tw[:-1].sum())
    keep = np.ones(m, bool)
    # planted anomaly 3: outage closes a restaurant for a week (30% go to a neighbour, rest are lost)
    for lid, s, e in C.CLOSURES:
        li = loc_ids.index(lid)
        d0 = (pd.Timestamp(s) - dates[0]).days; d1 = (pd.Timestamp(e) - dates[0]).days
        cl = (loc == li) & (day >= d0) & (day <= d1)
        moved = cl & (rng.random(m) < 0.30)
        loc[moved] = loc_ids.index("L02")
        keep &= ~(cl & ~moved)
    # planted anomaly 4: a restaurant loses a large share of orders from a given date
    lid, s, share = C.DECLINE_LOCATION
    d0 = (pd.Timestamp(s) - dates[0]).days
    keep &= ~((loc == loc_ids.index(lid)) & (day >= d0) & (rng.random(m) < share))
    sel = np.where(keep)[0]
    day, cust, kind, forced, loc = day[sel], cust[sel], kind[sel], forced[sel], loc[sel]
    m = len(day)

    # channel
    arch_row = np.where(cust >= 0, cu["arch"][np.maximum(cust, 0)], 7)
    probs = np.array(C.CHANNEL_P)[arch_row] * promo["CHF"][day]
    probs /= probs.sum(axis=1, keepdims=True)
    channel = (rng.random(m)[:, None] > np.cumsum(probs, axis=1)).sum(axis=1)
    channel = np.minimum(channel, 3)
    channel[kind == 2] = 1                                            # catering = takeaway

    # time of day
    dow = dates.dayofweek.values[day]
    weekend = dow >= 5
    online = channel >= 2
    hour = np.zeros(m, int)
    hours = np.array(C.HOURS)
    for we in (False, True):
        for on in (False, True):
            mk = (weekend == we) & (online == on)
            w = np.array(C.HOUR_W_WEEKEND if we else C.HOUR_W_WEEKDAY, float)
            if on: w = w * np.array(C.ONLINE_HOUR_TILT)
            hour[mk] = hours[rng.choice(len(hours), mk.sum(), p=w / w.sum())]
    hour[kind == 2] = rng.integers(10, 14, (kind == 2).sum())
    minute = rng.integers(0, 60, m); sec = rng.integers(0, 60, m)

    # chronological order -> order ids are chronological
    key = day.astype(np.int64) * 86400 + hour * 3600 + minute * 60 + sec
    o = np.argsort(key, kind="stable")
    day, cust, kind, loc, channel, hour, minute, sec = (x[o] for x in (day, cust, kind, loc, channel, hour, minute, sec))
    m = len(day)
    reg = cust >= 0
    first = np.zeros(m, bool)
    _, fi = np.unique(cust[reg], return_index=True)
    first[np.where(reg)[0][fi]] = True
    first_new = first & (cu["join"][np.maximum(cust, 0)] >= 0) & reg    # first order of a customer who joined in-period

    # promotions: eligibility x redemption chance (promo-driven customers redeem far more often)
    pidx = np.zeros(m, int)
    arch_o = np.where(reg, cu["arch"][np.maximum(cust, 0)], 7)
    order_p = sorted(range(len(C.PROMOS)), key=lambda i: C.PROMOS[i]["pct"])
    for p in order_p:
        pr = C.PROMOS[p]
        elig = promo["ACT"][p][day] & promo["CH_OK"][p + 1][channel]
        if pr["new_only"]: elig &= first_new
        if pr["loyal_only"]: elig &= reg & cu["loyal"][np.maximum(cust, 0)]
        prob = np.full(m, pr["redeem"])
        if not (pr["new_only"] or pr["loyal_only"]):
            prob = np.where(arch_o == 2, np.maximum(prob, 0.80), prob)
        take = elig & (rng.random(m) < prob)
        pidx[take] = p + 1
    pidx[kind == 2] = 0

    # planted anomaly 5: unusual 60-90% discounts without any promotion (one location)
    man_pct = np.zeros(m)
    ml, mn = C.MANUAL_DISCOUNT_LOC
    cands = np.where((loc == loc_ids.index(ml)) & (kind == 0))[0]
    mn = min(int(mn * scale) if scale < 1 else mn, len(cands))
    pick = rng.choice(cands, mn, replace=False)
    man_pct[pick] = rng.uniform(0.60, 0.90, mn); pidx[pick] = 0

    # status, payment, party size, delivery
    u = rng.random(m)
    D_ = C.DIRTY
    status = np.where(u < D_["status_cancelled"], "CANCELLED",
             np.where(u < D_["status_cancelled"] + D_["status_refunded"], "REFUNDED",
             np.where(u < D_["status_cancelled"] + D_["status_refunded"] + D_["status_void"], "VOID", "COMPLETED")))
    pay = np.empty(m, object)
    on = channel >= 2
    pay[on] = rng.choice(["CARD", "TRANSFER", "WALLET"], on.sum(), p=[0.5, 0.35, 0.15])
    pay[~on] = rng.choice(["CASH", "CARD", "TRANSFER", "POS"], (~on).sum(), p=[0.25, 0.30, 0.25, 0.20])
    pay[rng.random(m) < D_["payment_null"]] = None
    party = np.where(channel == 0, rng.choice([1, 2, 3, 4, 5, 6], m, p=[0.25, 0.38, 0.17, 0.12, 0.05, 0.03]), 0)
    extra = np.where(channel == 1, 1.6, np.where(channel == 2, 1.8, 1.9))
    k = np.where(channel == 0, np.round(party * 0.9 + rng.poisson(0.9, m)), 1 + rng.poisson(extra))
    k = np.clip(k, 1, 8).astype(int)
    k[kind == 2] = 7
    bulk = np.where(kind == 2, rng.integers(5, 20, m), 1)
    platform = np.empty(m, object)
    d3 = channel == 3
    platform[d3] = rng.choice(["PARTNER_A", "PARTNER_B", "PARTNER_C"], d3.sum(), p=[0.5, 0.3, 0.2])
    fee = np.where(d3, np.round(rng.uniform(800, 2500, m) / 50) * 50, 0.0)
    free_del = np.array([t == "FREE_DELIVERY" for t in promo["ptype"]])[pidx]
    fee = np.where(free_del, 0.0, fee)
    return dict(m=m, day=day, cust=cust, kind=kind, loc=loc, channel=channel, hour=hour, minute=minute, sec=sec,
                pidx=pidx, man_pct=man_pct, status=status, pay=pay, party=party, k=k, bulk=bulk,
                platform=platform, fee=fee, hgroup=np.select([hour <= 10, hour <= 14, hour <= 17], [0, 1, 2], 3))


# ============================================================================
# 5. ORDER LINES (chunked) + CSV PART FILES
# ============================================================================
def dirty_lines(rng, df, log_counts):
    """Inject invalid values into a chunk of order lines. Returns dirty df."""
    D_ = C.DIRTY
    n = len(df)

    def pick(rate):
        return np.where(rng.random(n) < rate)[0]

    r = pick(D_["line_qty_invalid"]); df.loc[r, "quantity"] = rng.choice([-1, -2, 0], len(r))
    log_counts["order_items.negative_or_zero_quantity"] += len(r)
    r2 = pick(D_["line_price_invalid"]); df.loc[r2, "unit_price"] = rng.choice([0.0, -1500.0], len(r2))
    log_counts["order_items.invalid_unit_price"] += len(r2)
    r3 = pick(D_["line_price_extreme"]); df.loc[r3, "unit_price"] = df.loc[r3, "unit_price"] * 100
    log_counts["order_items.extreme_unit_price"] += len(r3)
    r4 = pick(D_["line_discount_wrong"])
    df.loc[r4, "discount_amount"] = (df.loc[r4, "unit_price"] * df.loc[r4, "quantity"].abs() * rng.uniform(1.2, 3, len(r4))).round(2)
    log_counts["order_items.discount_exceeds_line_value"] += len(r4)
    touched = np.unique(np.concatenate([r, r2, r3, r4]))
    df.loc[touched, "line_total"] = (df.loc[touched, "unit_price"] * df.loc[touched, "quantity"] - df.loc[touched, "discount_amount"]).round(2)
    r5 = pick(D_["line_item_null"]); df.loc[r5, "item_id"] = None
    log_counts["order_items.missing_item_id"] += len(r5)
    r6 = pick(D_["line_item_unknown"]); df.loc[r6, "item_id"] = [f"M{x}" for x in rng.integers(900, 960, len(r6))]
    log_counts["order_items.unknown_item_id"] += len(r6)
    return df


def generate_orders_and_lines(rng, H, menu, arr, dm, PRICE, promo, dates, out_raw, chunk, log_counts):
    m = H["m"]
    N = len(menu); L = len(C.LOCATIONS); D = len(dates)
    item_ids = menu.item_id.values
    POP = arr["_pop"].astype(np.float32)
    PB, ELIG, PCT = promo["PB"], promo["ELIG"], promo["PCT"]
    ptype_free = np.array([t == "FREE_DELIVERY" for t in promo["ptype"]])
    loc_ids = np.array([l[0] for l in C.LOCATIONS])
    day64 = np.array(dates.values, dtype="datetime64[s]")
    ch_names = np.array(C.CHANNELS)
    os.makedirs(f"{out_raw}/orders", exist_ok=True)
    os.makedirs(f"{out_raw}/order_items", exist_ok=True)
    sold = np.zeros(D * L * N, np.float64)          # clean completed sales per (day, location, item)
    rate_lines = {"o": [], "i": [], "d": [], "l": [], "c": []}
    rate_orders = {"d": [], "l": [], "c": [], "ord": []}
    line_counter = 0
    near_counter = 0
    qty_cum = np.cumsum(C.QTY_P)
    n_chunks = int(np.ceil(m / chunk))
    total_lines = 0
    for ci in range(n_chunks):
        s, e = ci * chunk, min((ci + 1) * chunk, m)
        n = e - s
        sl = slice(s, e)
        d, l, hg, pp, kk = H["day"][sl], H["loc"][sl], H["hgroup"][sl], H["pidx"][sl], H["k"][sl]
        W0 = (POP[None, :] * dm["DAYITEM"][d] * dm["LOCAFF"][l] * dm["HOURM"][hg] * PB[pp]).astype(np.float32)
        chosen = np.zeros((n, N), bool)
        anchor = np.zeros(n, int)
        lo_, li_ = [], []
        for slot in range(8):
            act = np.where(kk > slot)[0]
            if len(act) == 0: break
            Ws = W0[act] * (dm["slot0"] if slot == 0 else dm["slotN"])[None, :]
            if slot > 0: Ws *= dm["PAIR"][anchor[act]]
            Ws[chosen[act]] = 0
            cs = np.cumsum(Ws, axis=1)
            u = rng.random(len(act)).astype(np.float32) * cs[:, -1]
            idx = np.minimum((cs < u[:, None]).sum(axis=1), N - 1)
            chosen[act, idx] = True
            if slot == 0: anchor[act] = idx
            lo_.append(act); li_.append(idx)
        ol = np.concatenate(lo_); it = np.concatenate(li_)
        srt = np.argsort(ol, kind="stable"); ol, it = ol[srt], it[srt]
        q = 1 + np.searchsorted(qty_cum, rng.random(len(ol)), side="right").clip(0, 4)
        q = q * H["bulk"][sl][ol]
        price = PRICE[d[ol], it].astype(np.float64)
        gross = q * price
        pl = pp[ol]
        disc = gross * PCT[pl] * ELIG[pl, it]
        man = H["man_pct"][sl][ol]
        disc = np.where(man > 0, gross * man, disc).round(2)
        subtotal = np.bincount(ol, gross, minlength=n)
        disc_tot = np.bincount(ol, disc, minlength=n)
        status = H["status"][sl]
        completed = status == "COMPLETED"
        # aggregate clean sales for wastage / inventory
        cl = completed[ol]
        flat = (d[ol][cl].astype(np.int64) * L + l[ol][cl]) * N + it[cl]
        sold += np.bincount(flat, weights=q[cl].astype(float), minlength=D * L * N)

        order_no = np.arange(s, e) + 1
        has_promo = (pp > 0) & ((disc_tot > 0) | ptype_free[pp])
        promo_ids = np.array([None] + [p["id"] for p in C.PROMOS], object)[np.where(has_promo, pp, 0)]
        net = subtotal - disc_tot
        fee = H["fee"][sl]
        ch = H["channel"][sl]
        pfee = np.where(ch == 3, 0.22 * net, np.where(ch == 2, 0.04 * net, 0.0)).round(2)
        total = (net + fee).round(2)
        ts = day64[d] + (H["hour"][sl] * 3600 + H["minute"][sl] * 60 + H["sec"][sl]).astype("timedelta64[s]")
        cust_ids = np.where(H["cust"][sl] >= 0, ids("CU", np.maximum(H["cust"][sl], 0) + 1, 6), None).astype(object)
        o_df = pd.DataFrame(dict(
            order_id=ids("ORD", order_no, 8), customer_id=cust_ids, location_id=loc_ids[l],
            order_datetime=pd.Series(ts).dt.strftime("%Y-%m-%d %H:%M:%S").values,
            channel=ch_names[ch], delivery_platform=H["platform"][sl], order_status=status, promo_id=promo_ids,
            party_size=np.where(ch == 0, H["party"][sl], 0), subtotal=subtotal.round(2), discount_total=disc_tot,
            delivery_fee=fee, platform_fee=pfee, total_amount=total, payment_method=H["pay"][sl]))
        o_df["party_size"] = o_df["party_size"].where(o_df["party_size"] > 0, np.nan)
        n_lines = len(ol)
        line_no = np.arange(line_counter + 1, line_counter + n_lines + 1)
        line_counter += n_lines
        l_df = pd.DataFrame(dict(
            order_line_id=ids("OL", line_no, 9), order_id=ids("ORD", order_no[ol], 8), item_id=item_ids[it],
            quantity=q.astype(int), unit_price=price, discount_amount=disc, line_total=(gross - disc).round(2)))

        # ratings sample (clean orders only) - kept as compact arrays
        rs = (rng.random(n_lines) < 0.10) & cl
        rate_lines["o"].append(order_no[ol][rs]); rate_lines["i"].append(it[rs]); rate_lines["d"].append(d[ol][rs])
        rate_lines["l"].append(l[ol][rs]); rate_lines["c"].append(H["cust"][sl][ol][rs])
        ro = (rng.random(n) < 0.08) & completed
        rate_orders["ord"].append(order_no[ro]); rate_orders["d"].append(d[ro]); rate_orders["l"].append(l[ro])
        rate_orders["c"].append(H["cust"][sl][ro])

        # ---- DIRT ---------------------------------------------------------------------------
        l_df = dirty_lines(rng, l_df, log_counts)
        D_ = C.DIRTY
        # near-duplicate orders: same content, new id, 1-3 minutes later
        k_near = np.where((rng.random(n) < D_["dup_order_near"]) & completed)[0]
        if len(k_near):
            src_ids = o_df.order_id.values[k_near]
            new_ids = ids("ORD", 90000000 + near_counter + np.arange(len(k_near)), 8)
            near_counter += len(k_near)
            mp = dict(zip(src_ids, new_ids))
            near_o = o_df.iloc[k_near].copy()
            near_o["order_id"] = new_ids
            near_o["order_datetime"] = (pd.to_datetime(near_o.order_datetime)
                                        + pd.to_timedelta(rng.integers(1, 4, len(k_near)), unit="m")).dt.strftime("%Y-%m-%d %H:%M:%S")
            near_l = l_df[l_df.order_id.isin(src_ids)].copy()
            near_l["order_id"] = near_l.order_id.map(mp)
            near_l["order_line_id"] = ids("OL9", near_counter * 100 + np.arange(len(near_l)), 8)
            o_df = pd.concat([o_df, near_o], ignore_index=True); l_df = pd.concat([l_df, near_l], ignore_index=True)
            log_counts["orders.near_duplicate_transactions"] += len(k_near)
        # exact duplicates (same primary key twice)
        dup_o = o_df.sample(frac=D_["dup_order_exact"], random_state=int(rng.integers(1e9)))
        o_df = pd.concat([o_df, dup_o], ignore_index=True)
        log_counts["orders.exact_duplicate_order_rows"] += len(dup_o)
        dup_l = l_df.sample(frac=D_["dup_line_exact"], random_state=int(rng.integers(1e9)))
        l_df = pd.concat([l_df, dup_l], ignore_index=True)
        log_counts["order_items.exact_duplicate_line_rows"] += len(dup_l)
        # invalid dates / locations in headers
        n_o = len(o_df)
        bad = rng.random(n_o) < D_["order_date_invalid"]
        o_df.loc[bad, "order_datetime"] = rng.choice(
            ["2026-13-45 10:15:00", "31/02/2026 12:00", "0000-00-00 00:00:00", "2027-03-14 19:45:00",
             "1900-01-01 00:00:00", "not_a_date"], bad.sum())
        log_counts["orders.invalid_dates"] += int(bad.sum())
        badl = rng.random(n_o) < D_["order_loc_invalid"]
        o_df.loc[badl, "location_id"] = "L99"
        log_counts["orders.invalid_location_id"] += int(badl.sum())
        nl = rng.random(n_o) < D_["order_loc_null"]
        o_df.loc[nl, "location_id"] = None
        log_counts["orders.missing_location_id"] += int(nl.sum())
        o_df.to_csv(f"{out_raw}/orders/orders_part_{ci + 1:03d}.csv", index=False)
        l_df.to_csv(f"{out_raw}/order_items/order_items_part_{ci + 1:03d}.csv", index=False)
        total_lines += len(l_df)
        log(f"chunk {ci + 1}/{n_chunks}: {len(o_df):,} orders, {len(l_df):,} lines written")
        del W0, chosen
    log_counts["_clean_order_count"] = m
    log_counts["_clean_line_count"] = line_counter
    cat = lambda dct, k: np.concatenate(dct[k])
    rl = {k: cat(rate_lines, k) for k in rate_lines}
    ro = {k: cat(rate_orders, k) for k in rate_orders}
    return sold.reshape(D, L, N), rl, ro


# ============================================================================
# 6. RATINGS
# ============================================================================
def build_ratings(rng, rl, ro, menu, arr, dates, n_cust, scale, log_counts, anomalies):
    N = len(menu); L = len(C.LOCATIONS); D = len(dates)
    names = menu.item_name.values
    loc_eff = rng.normal(0, 0.12, L)
    q_item = arr["_q"]
    # item-level ratings tied to a real order line
    v = np.clip(np.round(rng.normal(q_item[rl["i"]] + loc_eff[rl["l"]], 0.85)), 1, 5)
    delay = rng.integers(0, 3, len(v))
    it_df = pd.DataFrame(dict(order_no=rl["o"], customer=rl["c"], item=rl["i"], loc=rl["l"],
                              rating_value=v, day=np.minimum(rl["d"] + delay, D - 1)))
    v2 = np.clip(np.round(rng.normal(4.05 + loc_eff[ro["l"]], 0.9)), 1, 5)
    lo_df = pd.DataFrame(dict(order_no=ro["ord"], customer=ro["c"], item=-1, loc=ro["l"], rating_value=v2,
                              day=np.minimum(ro["d"] + rng.integers(0, 3, len(v2)), D - 1)))
    df = pd.concat([it_df, lo_df], ignore_index=True)
    df["source"] = rng.choice(["APP", "QR_CODE", "EMAIL_SURVEY", "DELIVERY_PLATFORM"], len(df), p=[0.4, 0.25, 0.15, 0.2])
    extra = []
    loc_ids = [l[0] for l in C.LOCATIONS]

    def day_of(s): return (pd.Timestamp(s) - dates[0]).days

    def add(nrows, item, loc, d0, d1, value, cust, kind, note):
        dd = rng.integers(day_of(d0), day_of(d1) + 1, nrows)
        extra.append(pd.DataFrame(dict(order_no=np.nan, customer=cust, item=item, loc=loc, rating_value=value,
                                       day=dd, source="APP")))
        anomalies.append(dict(type=kind, detail=note, rows=int(nrows)))

    sc = max(0.2, scale)
    ti = int(np.where(names == "Gourmet Truffle Burger")[0][0])
    add(int(300 * sc), ti, rng.integers(0, L - 1, int(300 * sc)), "2026-08-20", "2026-08-21", 5,
        rng.choice(n_cust, int(300 * sc)), "RATING_SPIKE_FAKE_REVIEWS",
        "Gourmet Truffle Burger: 5-star burst from ~40 accounts with no matching purchases (Aug 20-21)")
    tj = int(np.where(names == "Grilled Tilapia")[0][0])
    add(int(120 * sc), tj, loc_ids.index("L05"), "2026-03-10", "2026-03-16", 1, rng.choice(n_cust, int(120 * sc)),
        "RATING_DROP", "Grilled Tilapia at L05 Yaba: sudden run of 1-star ratings (Mar 10-16)")
    tt = int(np.where(names == "Tiramisu")[0][0])
    one = int(rng.integers(0, n_cust))
    add(int(60 * sc), tt, rng.integers(0, L - 1, int(60 * sc)), "2026-04-12", "2026-04-12", 5, one,
        "EXCESSIVE_IDENTICAL_RATINGS", f"One customer (index {one}) posted identical 5-star Tiramisu ratings on Apr 12")
    add(int(400 * sc), -1, loc_ids.index("L09"), "2026-06-20", "2026-06-20", 5, rng.choice(n_cust, int(400 * sc)),
        "RATING_VOLUME_SPIKE", "L09 Festac: hundreds of 5-star location ratings in one day (Jun 20)")
    df = pd.concat([df] + extra, ignore_index=True).sort_values(["day"], kind="stable").reset_index(drop=True)
    n = len(df)
    bad = rng.random(n) < C.DIRTY["rating_invalid"]
    rv = df.rating_value.values.astype(float)
    rv[bad] = rng.choice([0, 6, -1, 11], bad.sum())
    log_counts["ratings.invalid_rating_value"] += int(bad.sum())
    out = pd.DataFrame(dict(
        rating_id=ids("RT", np.arange(1, n + 1), 8),
        order_id=np.where(df.order_no.notna(), ids("ORD", df.order_no.fillna(0).astype(int), 8), None).astype(object),
        customer_id=np.where(df.customer >= 0, ids("CU", df.customer.clip(lower=0).astype(int) + 1, 6), None).astype(object),
        item_id=np.where(df.item >= 0, menu.item_id.values[df.item.clip(lower=0).astype(int)], None).astype(object),
        location_id=np.array(loc_ids, object)[df["loc"].astype(int)],
        rating_value=rv.astype(int), rating_date=(dates[0] + pd.to_timedelta(df.day.values, unit="D")).strftime("%Y-%m-%d"),
        source=df.source.values))
    badloc = rng.random(n) < 0.0005
    out.loc[badloc, "location_id"] = "L00"
    log_counts["ratings.invalid_location_id"] += int(badloc.sum())
    return out


# ============================================================================
# 7. WASTAGE and INVENTORY (derived from simulated sales)
# ============================================================================
def build_wastage(rng, sold, menu, arr, COST, promo, dates, scale, log_counts):
    D, L, N = sold.shape
    loc_ids = np.array([l[0] for l in C.LOCATIONS])
    open_idx = np.array([(pd.Timestamp(l[6]) - dates[0]).days for l in C.LOCATIONS])
    d_arr = np.arange(D)
    open_mask = d_arr[:, None] >= open_idx[None, :]
    for lid, s, e in C.CLOSURES:
        li = list(loc_ids).index(lid)
        open_mask[(pd.Timestamp(s) - dates[0]).days:(pd.Timestamp(e) - dates[0]).days + 1, li] = False
    avail = (d_arr[:, None] >= arr["_from"][None, :]) & (d_arr[:, None] <= arr["_to"][None, :])
    locfac = np.ones((D, L))
    lid, s, share = C.DECLINE_LOCATION
    locfac[(pd.Timestamp(s) - dates[0]).days:, list(loc_ids).index(lid)] = 1.8   # keeps preparing as before the drop
    lam = (sold + 0.3) * arr["_over"][None, None, :] * promo["OVER"][:, None, :] * locfac[:, :, None]
    lam *= (avail[:, None, :] & open_mask[:, :, None])
    waste = rng.poisson(lam)
    d, l, i = np.nonzero(waste)
    qty = waste[d, l, i].astype(float)
    n = len(d)
    prep = sold[d, l, i] + qty
    over_active = promo["OVER"][d, i] > 1.0
    reason = rng.choice(["OVERPRODUCTION", "SPOILAGE", "EXPIRED", "PREP_ERROR", "DROPPED_OR_SPILLED",
                         "CUSTOMER_RETURN"], n, p=[0.50, 0.20, 0.12, 0.08, 0.06, 0.04]).astype(object)
    reason[over_active & (rng.random(n) < 0.85)] = "OVERPRODUCTION"
    cost = (qty * COST[d, i]).round(2)
    weight = menu.portion_weight_g.values[i]
    unit = np.full(n, "portion", object)
    qty_out = qty.copy()
    u = rng.random(n)
    DT = C.DIRTY
    c1 = u < DT["wastage_unit_kg"]
    unit[c1] = "kg"; qty_out[c1] = (qty[c1] * weight[c1] / 1000).round(3)
    c2 = (u >= DT["wastage_unit_kg"]) & (u < DT["wastage_unit_kg"] + DT["wastage_unit_g"])
    unit[c2] = "g"; qty_out[c2] = qty[c2] * weight[c2]
    t3 = DT["wastage_unit_kg"] + DT["wastage_unit_g"]
    c3 = (u >= t3) & (u < t3 + DT["wastage_unit_pcs"]); unit[c3] = "pcs"
    c4 = (u >= t3 + DT["wastage_unit_pcs"]) & (u < t3 + DT["wastage_unit_pcs"] + DT["wastage_unit_case"])
    unit[c4] = rng.choice(["Portion", "PORTION", "portions"], c4.sum())
    log_counts["wastage.inconsistent_units"] += int(c1.sum() + c2.sum() + c3.sum() + c4.sum())
    df = pd.DataFrame(dict(
        wastage_id=ids("WS", np.arange(1, n + 1), 8), wastage_date=(dates[0] + pd.to_timedelta(d, unit="D")).strftime("%Y-%m-%d"),
        location_id=loc_ids[l], item_id=menu.item_id.values[i],
        shift=rng.choice(["MORNING", "AFTERNOON", "EVENING"], n, p=[0.2, 0.35, 0.45]),
        prep_quantity=prep.round(0), quantity_wasted=qty_out, unit=unit, wastage_cost=cost, reason=reason))
    imp = rng.random(n) < DT["wastage_impossible"]
    df.loc[imp, "quantity_wasted"] = rng.choice([-3.0, 9999.0, 250.0], imp.sum())
    log_counts["wastage.impossible_quantities"] += int(imp.sum())
    bl = rng.random(n) < DT["wastage_loc_invalid"]; df.loc[bl, "location_id"] = "L00"
    log_counts["wastage.invalid_location_id"] += int(bl.sum())
    bi = rng.random(n) < DT["wastage_item_null"]; df.loc[bi, "item_id"] = None
    log_counts["wastage.missing_item_id"] += int(bi.sum())
    return df, waste, open_mask, avail


def build_inventory(rng, sold, waste, menu, open_mask, avail, dates, log_counts):
    D, L, N = sold.shape
    W = int(np.ceil(D / 7))
    loc_ids = np.array([l[0] for l in C.LOCATIONS])
    wk = np.arange(D) // 7
    sold_w = np.zeros((W, L, N)); waste_w = np.zeros((W, L, N)); act_w = np.zeros((W, L, N), bool)
    for w in range(W):
        sel = wk == w
        sold_w[w] = sold[sel].sum(axis=0); waste_w[w] = waste[sel].sum(axis=0)
        act_w[w] = (avail[sel][:, None, :] & open_mask[sel][:, :, None]).any(axis=0)
    cons = sold_w + waste_w
    target = np.ceil(cons.mean(axis=0) * 1.8 + 2)
    opening = np.ceil(target * 1.2)
    rows = []
    for w in range(W):
        c = cons[w]
        repl = np.clip(np.round(target * rng.uniform(0.8, 1.2, (L, N)) - np.maximum(opening - c, 0)), 0, None)
        avail_stock = opening + repl
        stockout = avail_stock < c
        closing = np.maximum(avail_stock - c, 0)
        l, i = np.nonzero(act_w[w])
        rows.append(pd.DataFrame(dict(
            week_start_date=(dates[0] + pd.Timedelta(days=7 * w)).strftime("%Y-%m-%d"), location_id=loc_ids[l],
            item_id=menu.item_id.values[i], opening_stock=opening[l, i], replenished_qty=repl[l, i],
            consumed_qty=c[l, i], closing_stock=closing[l, i], reorder_level=np.ceil(target[l, i] * 0.5),
            stockout_flag=stockout[l, i], unit="portion")))
        opening = closing
    inv = pd.concat(rows, ignore_index=True)
    n = len(inv)
    inv.insert(0, "inventory_id", ids("INV", np.arange(1, n + 1), 8))
    DT = C.DIRTY
    neg = rng.random(n) < DT["inventory_neg"]; inv.loc[neg, "closing_stock"] = -rng.integers(1, 30, neg.sum())
    log_counts["inventory.negative_closing_stock"] += int(neg.sum())
    bl = rng.random(n) < DT["inventory_loc_invalid"]; inv.loc[bl, "location_id"] = "L00"
    log_counts["inventory.invalid_location_id"] += int(bl.sum())
    kg = rng.random(n) < 0.02
    wgt = menu.portion_weight_g.values[menu.item_id.reset_index(drop=True).searchsorted(inv.item_id.values)
                                       if False else pd.Index(menu.item_id).get_indexer(inv.item_id)]
    for c in ["opening_stock", "replenished_qty", "consumed_qty", "closing_stock"]:
        inv.loc[kg, c] = (inv.loc[kg, c] * wgt[kg] / 1000).round(2)
    inv.loc[kg, "unit"] = "kg"
    log_counts["inventory.inconsistent_units"] += int(kg.sum())
    return inv


# ============================================================================
# 8. MAIN
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description="DineIQ synthetic dataset generator")
    ap.add_argument("--out", default="..", help="project root (raw_data/ is created inside)")
    ap.add_argument("--scale", type=float, default=1.0, help="1.0 = full size; 0.05 = quick smoke test")
    ap.add_argument("--chunk-orders", type=int, default=30000)
    ap.add_argument("--seed", type=int, default=C.SEED)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    out_raw = os.path.join(args.out, "raw_data")
    if os.path.exists(out_raw): shutil.rmtree(out_raw)
    os.makedirs(os.path.join(out_raw, "_ground_truth"))
    dates = pd.date_range(C.START_DATE, periods=C.N_DAYS)
    log_counts = {k: 0 for k in ["orders.near_duplicate_transactions", "orders.exact_duplicate_order_rows",
                                 "orders.invalid_dates", "orders.invalid_location_id", "orders.missing_location_id",
                                 "order_items.exact_duplicate_line_rows", "order_items.negative_or_zero_quantity",
                                 "order_items.invalid_unit_price", "order_items.extreme_unit_price",
                                 "order_items.discount_exceeds_line_value", "order_items.missing_item_id",
                                 "order_items.unknown_item_id", "ratings.invalid_rating_value",
                                 "ratings.invalid_location_id", "wastage.inconsistent_units",
                                 "wastage.impossible_quantities", "wastage.invalid_location_id",
                                 "wastage.missing_item_id", "inventory.negative_closing_stock",
                                 "inventory.invalid_location_id", "inventory.inconsistent_units",
                                 "customers.duplicate_rows", "customers.missing_age_band",
                                 "pricing_history.invalid_price_rows"]}
    anomalies = []

    log("building static tables")
    cats = build_categories()
    menu, arr, item_truth = build_menu(rng, dates[0])
    locs = build_locations()
    ph, PRICE, COST = build_price_history(rng, menu, C.N_DAYS, dates[0])
    promo = build_promotions(menu, dates)
    dm = build_demand_matrices(rng, menu, arr, locs, dates, PRICE)
    cums = build_day_weights(dates, promo)
    n_cust = int(55000 * args.scale)
    customers, cust_truth, cu = build_customers(rng, n_cust, locs, dates)
    log(f"{len(menu)} menu items, {len(locs)} locations, {n_cust:,} customers, {len(promo['promos'])} promotions")

    log("building order headers")
    H = build_order_headers(rng, cu, locs, dates, cums, promo, args.scale)
    log(f"{H['m']:,} orders planned")

    log("generating order lines in chunks")
    sold, rl, ro = generate_orders_and_lines(rng, H, menu, arr, dm, PRICE, promo, dates, out_raw,
                                             args.chunk_orders, log_counts)
    log("ratings")
    ratings = build_ratings(rng, rl, ro, menu, arr, dates, n_cust, args.scale, log_counts, anomalies)
    log("wastage and inventory")
    wastage, waste_arr, open_mask, avail = build_wastage(rng, sold, menu, arr, COST, promo, dates, args.scale, log_counts)
    inventory = build_inventory(rng, sold, waste_arr, menu, open_mask, avail, dates, log_counts)

    # ---- dirt on small tables --------------------------------------------------------------
    log_counts["customers.missing_age_band"] = int(customers.age_band.isna().sum())
    dupc = customers.sample(frac=C.DIRTY["dup_customer"], random_state=7)
    customers = pd.concat([customers, dupc], ignore_index=True)
    log_counts["customers.duplicate_rows"] = len(dupc)
    bad_rows = rng.choice(len(ph), C.DIRTY["price_invalid_rows"], replace=False)
    ph.loc[bad_rows, "price"] = rng.choice([0.0, -4500.0, 4500000.0], len(bad_rows))
    log_counts["pricing_history.invalid_price_rows"] = len(bad_rows)

    # ---- write small tables ----------------------------------------------------------------
    log("writing CSV files")
    w = lambda df, name: df.to_csv(f"{out_raw}/{name}.csv", index=False)
    w(cats, "menu_categories"); w(menu, "menu_items"); w(locs, "restaurants"); w(customers, "customers")
    w(ph, "pricing_history"); w(promo["promos"], "promotions"); w(promo["promo_items"], "promotion_items")
    w(ratings, "ratings"); w(wastage, "wastage"); w(inventory, "inventory")

    # ---- ground truth (for TESTING your analytics - never use as ML features) --------------
    gt = f"{out_raw}/_ground_truth"
    item_truth.to_csv(f"{gt}/items_truth.csv", index=False)
    cust_truth.to_csv(f"{gt}/customers_truth.csv", index=False)
    promo["truth"].to_csv(f"{gt}/promotions_truth.csv", index=False)
    anomalies += [
        dict(type="SALES_SPIKE", detail=f"{C.SPIKE_EVENT[0]} on {C.SPIKE_EVENT[1]}: one-day event, extra orders"),
        dict(type="SALES_DROP_OUTAGE", detail=f"{C.CLOSURES[0][0]} closed {C.CLOSURES[0][1]}..{C.CLOSURES[0][2]}"),
        dict(type="SALES_DROP_COMPETITOR", detail=f"{C.DECLINE_LOCATION[0]} loses {int(C.DECLINE_LOCATION[2]*100)}% of orders from {C.DECLINE_LOCATION[1]}"),
        dict(type="ABNORMAL_ORDER_VALUE", detail=f"{max(5, int(C.N_CATERING_ORDERS*args.scale))} corporate catering orders (bulk quantities)"),
        dict(type="UNUSUAL_DISCOUNTS", detail=f"{C.MANUAL_DISCOUNT_LOC[0]}: orders with 60-90% manual discount and no promotion"),
        dict(type="UNEXPECTED_DEMAND", detail="Suya Pizza goes viral 2026-08-26..2026-09-01 right after launch"),
        dict(type="NEW_LOCATION", detail="L24 Jabi Lake opens 2026-03-01"),
    ]
    json.dump(anomalies, open(f"{gt}/anomalies_truth.json", "w"), indent=2)
    log_counts["_note"] = "keys starting with _ are clean-record counts, not injected dirt"
    json.dump(log_counts, open(f"{gt}/injection_log.json", "w"), indent=2)
    log("DONE")


if __name__ == "__main__":
    main()
