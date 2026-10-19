"""
config.py - every business assumption of the DineIQ synthetic dataset lives here.

Why a separate config file?
  * The generator (generate_dataset.py) stays pure logic; this file is pure data.
  * During the final evaluation you may be asked for a "surprise modification"
    (add a location, add a category, change a threshold). Most of those are
    one-line edits in this file.

Currency: Nigerian Naira (NGN).  Period: 365 days, 2025-10-01 .. 2026-09-30.
"""

SEED = 42
START_DATE = "2025-10-01"
N_DAYS = 365

# --------------------------------------------------------------------------
# 1. MENU CATEGORIES
# id, name, perishability, meal_period, typical cost ratio (cost/price),
# weight of the category as the FIRST item of an order (slot0),
# weight as an ADD-ON item (slotN), base wastage rate
# --------------------------------------------------------------------------
CATEGORIES = [
    ("C01", "Starters",              "MEDIUM", "ALL_DAY",   0.34, 0.6, 1.0, 0.050),
    ("C02", "Soups & Stews",         "MEDIUM", "ALL_DAY",   0.36, 1.3, 0.3, 0.050),
    ("C03", "Rice & Grains",         "MEDIUM", "ALL_DAY",   0.33, 1.8, 0.4, 0.045),
    ("C04", "Grills & BBQ",          "MEDIUM", "ALL_DAY",   0.40, 1.5, 0.4, 0.050),
    ("C05", "Burgers & Sandwiches",  "LOW",    "ALL_DAY",   0.38, 1.6, 0.3, 0.035),
    ("C06", "Pizza & Pasta",         "LOW",    "ALL_DAY",   0.30, 1.5, 0.3, 0.040),
    ("C07", "Sides",                 "MEDIUM", "ALL_DAY",   0.28, 0.2, 1.8, 0.055),
    ("C08", "Desserts",              "HIGH",   "ALL_DAY",   0.27, 0.1, 1.2, 0.070),
    ("C09", "Cold Drinks",           "LOW",    "ALL_DAY",   0.24, 0.4, 2.5, 0.030),
    ("C10", "Hot Drinks",            "LOW",    "ALL_DAY",   0.20, 0.5, 0.8, 0.025),
    ("C11", "Kids Meals",            "MEDIUM", "ALL_DAY",   0.34, 0.5, 0.3, 0.050),
    ("C12", "Breakfast & Brunch",    "HIGH",   "BREAKFAST", 0.32, 0.8, 0.2, 0.060),
]

# --------------------------------------------------------------------------
# 2. MENU CATALOG  (name, launch price in NGN)  - 14 items x 12 categories = 168
# --------------------------------------------------------------------------
CATALOG = {
 "C01": [("Peppered Snail",6500),("Chicken Wings",5500),("Spring Rolls",3500),("Moi Moi Platter",3000),
         ("Puff Puff Bites",2000),("Suya Skewers",4500),("Calamari Rings",6000),("Bruschetta",3800),
         ("Garlic Prawns",8500),("Nachos Supreme",5200),("Stuffed Mushrooms",4200),("Akara Bites",2200),
         ("Gizdodo",5000),("Plantain Chips Dip",2800)],
 "C02": [("Egusi Soup",6000),("Ogbono Soup",6000),("Efo Riro",5800),("Okra Soup",5500),("Banga Soup",6500),
         ("Pepper Soup Goat",7000),("Pepper Soup Catfish",7500),("Tomato Basil Soup",3800),
         ("Chicken Noodle Soup",4200),("Mushroom Cream Soup",4200),("Oxtail Stew",9000),
         ("Ayamase Stew",6800),("Afang Soup",6500),("Seafood Chowder",8500)],
 "C03": [("Jollof Rice",3500),("Fried Rice",3800),("Coconut Rice",4000),("Ofada Rice",5200),
         ("Native Jollof",4200),("Basmati Pilau",4500),("Beans & Plantain",3200),("Ewa Agoyin",3500),
         ("Yam Porridge",4000),("Fisherman Rice",7500),("Mushroom Risotto",6500),("Egg Fried Rice",4200),
         ("White Rice & Stew",3300),("Concoction Rice",4500)],
 "C04": [("Grilled Chicken Half",7500),("Grilled Tilapia",8500),("Asun Peppered Goat",6500),
         ("Suya Platter",6000),("BBQ Ribs",11000),("Grilled Salmon",15000),("Beef Steak",16000),
         ("Lamb Chops",17500),("Turkey Wings",8000),("Peppered Croaker",9000),("Grilled Prawns",13000),
         ("Chicken Shawarma Plate",6500),("Mixed Grill Platter",18000),("Boli & Fish",5500)],
 "C05": [("Classic Beef Burger",5500),("Double Cheeseburger",7000),("Chicken Burger",5800),
         ("Spicy Chicken Burger",6200),("Veggie Burger",5000),("Club Sandwich",5500),
         ("Chicken Shawarma Wrap",4500),("Beef Shawarma Wrap",4800),("Hot Dog Classic",3500),
         ("Fish Burger",5800),("BLT Sandwich",5000),("Philly Steak Sandwich",7500),("Egg Sandwich",3500),
         ("Gourmet Truffle Burger",12000)],
 "C06": [("Margherita Pizza",7500),("Pepperoni Pizza",9500),("BBQ Chicken Pizza",10000),
         ("Veggie Supreme Pizza",8800),("Suya Pizza",10500),("Seafood Pizza",12500),
         ("Spaghetti Bolognese",6500),("Chicken Alfredo",7500),("Creamy Seafood Pasta",9500),
         ("Penne Arrabbiata",5800),("Lasagna",8000),("Carbonara",7200),("Stir-Fry Noodles",5500),
         ("Jollof Spaghetti",4000)],
 "C07": [("French Fries",2500),("Fried Plantain",1800),("Coleslaw",1500),("Garden Salad",3200),
         ("Moi Moi",1200),("Fried Yam",2500),("Sweet Potato Fries",2800),("Onion Rings",2600),
         ("Garlic Bread",2200),("Boiled Plantain",1500),("Mashed Potato",2000),("Steamed Veg",2000),
         ("Eba",1000),("Pounded Yam",1800)],
 "C08": [("Chocolate Lava Cake",4500),("Cheesecake",4800),("Ice Cream Sundae",3500),("Fruit Salad",3000),
         ("Chin Chin Jar",2500),("Banana Split",4000),("Tiramisu",5000),("Brownie with Ice Cream",4200),
         ("Waffle & Syrup",4200),("Crepe Nutella",4000),("Apple Pie",3800),("Coconut Pudding",3200),
         ("Puff Puff & Chocolate",3000),("Yoghurt Parfait",3200)],
 "C09": [("Cola 50cl",1000),("Orange Soda 50cl",1000),("Chapman",2500),("Zobo",1800),("Kunu",1500),
         ("Fresh Orange Juice",2800),("Pineapple Juice",2800),("Watermelon Juice",2800),("Bottled Water",600),
         ("Sparkling Water",1200),("Iced Tea",2200),("Lemonade",2200),("Smoothie Mango",3800),
         ("Malt Drink",1200)],
 "C10": [("Espresso",2000),("Americano",2500),("Cappuccino",3200),("Latte",3500),("Hot Chocolate",3200),
         ("Green Tea",2200),("Masala Tea",2200),("Ginger Tea",2000),("Mocha",3800),("Flat White",3500),
         ("Iced Coffee",3800),("Caramel Macchiato",4200),("Hot Lemon Honey",2200),
         ("Chocolate Malt Drink",2500)],
 "C11": [("Kids Chicken Nuggets",3500),("Kids Mini Burger",3200),("Kids Jollof & Chicken",3500),
         ("Kids Pasta",3000),("Kids Fish Fingers",3500),("Kids Pizza",3800),("Kids Fries Combo",2800),
         ("Kids Pancakes",3000),("Kids Sausage Roll",2200),("Kids Fruit Cup",2200),("Kids Mac & Cheese",3200),
         ("Kids Egg & Toast",2500),("Kids Rice & Stew",3000),("Kids Milkshake",2800)],
 "C12": [("Full English Breakfast",8500),("Akara & Pap",3500),("Pancake Stack",4800),("Cheese Omelette",4200),
         ("Yam & Egg",4500),("Bread & Egg Sauce",3500),("Avocado Toast",5000),("French Toast",4500),
         ("Breakfast Burrito",5500),("Oatmeal Bowl",3500),("Fruit & Yoghurt Bowl",4000),
         ("Sausage & Egg Roll",3200),("Shakshuka",5200),("Granola Bowl",4200)],
}

VEGETARIAN = {"Spring Rolls","Moi Moi Platter","Puff Puff Bites","Bruschetta","Stuffed Mushrooms","Akara Bites",
              "Plantain Chips Dip","Tomato Basil Soup","Mushroom Cream Soup","Beans & Plantain","Yam Porridge",
              "Mushroom Risotto","Margherita Pizza","Veggie Supreme Pizza","Penne Arrabbiata","Jollof Spaghetti",
              "French Fries","Fried Plantain","Coleslaw","Garden Salad","Moi Moi","Fried Yam","Sweet Potato Fries",
              "Onion Rings","Garlic Bread","Boiled Plantain","Mashed Potato","Steamed Veg","Eba","Pounded Yam",
              "Veggie Burger","Chocolate Lava Cake","Cheesecake","Ice Cream Sundae","Fruit Salad","Chin Chin Jar",
              "Banana Split","Tiramisu","Waffle & Syrup","Crepe Nutella","Apple Pie","Coconut Pudding",
              "Puff Puff & Chocolate","Yoghurt Parfait","Akara & Pap","Pancake Stack",
              "Avocado Toast","French Toast","Oatmeal Bowl","Fruit & Yoghurt Bowl","Granola Bowl","Shakshuka"}

# --------------------------------------------------------------------------
# 3. PLANTED MENU ARCHETYPES  (the "tricky cases" required by SRS Step 11)
#    The ground-truth file written next to the data records these labels so
#    you can later CHECK your classifier - never use them as ML features.
# --------------------------------------------------------------------------
ARCHETYPE = {
    # high demand + high margin
    "STAR": ["Jollof Rice","Grilled Chicken Half","Pepperoni Pizza","Egusi Soup","Fried Rice","Suya Platter",
             "Chapman","Cappuccino","French Fries","Chicken Wings"],
    # high demand, thin margin (one of them also has a poor rating: Hot Dog Classic)
    "VOLUME": ["Classic Beef Burger","Cola 50cl","Spaghetti Bolognese","White Rice & Stew","Hot Dog Classic",
               "Orange Soda 50cl"],
    # high demand but LOSS-MAKING: cost climbs above price during the year
    "LOSS_MAKER": ["Double Cheeseburger","Beef Shawarma Wrap"],
    # rarely ordered but very profitable and loved
    "HIDDEN_GEM": ["Ofada Rice","Ayamase Stew","Tiramisu","Zobo","Shakshuka","Asun Peppered Goat",
                   "Peppered Snail","Banga Soup"],
    # popular but a lot of it is thrown away
    "WASTE_HEAVY": ["Garden Salad","Fresh Orange Juice","Fruit Salad","Moi Moi","Pepper Soup Catfish"],
    # weak demand, weak margin, poor ratings
    "LOW_PERFORMER": ["Seafood Chowder","Concoction Rice","Veggie Burger","Steamed Veg","Boiled Plantain",
                      "Oatmeal Bowl","Apple Pie","Coconut Pudding","Kids Egg & Toast","Granola Bowl",
                      "Mushroom Cream Soup","Stir-Fry Noodles"],
}
POP_FACTOR = {"STAR":3.2,"VOLUME":3.0,"LOSS_MAKER":2.6,"HIDDEN_GEM":0.22,"WASTE_HEAVY":1.8,
              "LOW_PERFORMER":0.30,"BASE":1.0}
# absolute cost ratio ranges (cost/price) for planted archetypes; BASE uses the category ratio
COST_RATIO = {"STAR":(0.24,0.30),"VOLUME":(0.64,0.74),"LOSS_MAKER":(0.97,0.97),
              "HIDDEN_GEM":(0.18,0.24),"LOW_PERFORMER":(0.55,0.70)}
# mean customer rating (1-5) per archetype; QUALITY_OVERRIDE wins when present
QUALITY = {"STAR":4.4,"VOLUME":3.9,"LOSS_MAKER":4.2,"HIDDEN_GEM":4.6,"WASTE_HEAVY":4.0,
           "LOW_PERFORMER":3.1,"BASE":4.0}
QUALITY_OVERRIDE = {"Double Cheeseburger":4.6,   # highly rated but loses money
                    "Hot Dog Classic":2.9,       # low rating but sells a lot
                    "Tiramisu":4.7}

PRICE_SENSITIVE = ["Chicken Shawarma Wrap","Jollof Spaghetti","Ice Cream Sundae","Malt Drink",
                   "Sweet Potato Fries","Fried Plantain"]           # elasticity ~ -2.4
LOW_SENSITIVITY = ["Beef Steak","Grilled Salmon","Lamb Chops","Mixed Grill Platter","Espresso","Cappuccino"]
PROMO_DEPENDENT = ["Veggie Supreme Pizza","Chicken Alfredo","Banana Split","Brownie with Ice Cream"]
WEEKEND_ITEMS = ["BBQ Ribs","Mixed Grill Platter","Full English Breakfast","Pancake Stack","Waffle & Syrup",
                 "Boli & Fish"]
COLD_WEATHER_ITEMS = ["Pepper Soup Goat","Pepper Soup Catfish","Ogbono Soup","Okra Soup","Hot Chocolate",
                      "Masala Tea","Ginger Tea","Yam Porridge","Chicken Noodle Soup","Tomato Basil Soup"]
HOT_WEATHER_ITEMS = ["Smoothie Mango","Watermelon Juice","Iced Tea","Lemonade","Iced Coffee","Ice Cream Sundae",
                     "Banana Split","Fruit Salad","Kunu"]
# month 1..12 multipliers
SEASON_PROFILE = {
    "COLD_WEATHER": [1.3,1.0,0.6,0.7,1.2,1.6,1.7,1.7,1.5,1.3,1.0,1.2],
    "HOT_WEATHER":  [1.0,1.4,1.7,1.6,1.2,0.8,0.6,0.6,0.8,1.0,1.2,1.0],
}
# items that exist only inside a window (seasonal / limited-time menu items)
LIMITED_WINDOWS = {"Turkey Wings":("2025-11-15","2026-01-10"),
                   "Chin Chin Jar":("2025-12-01","2026-01-10"),
                   "Hot Lemon Honey":("2025-12-01","2026-02-28"),
                   "Watermelon Juice":("2026-02-01","2026-04-30"),
                   "Smoothie Mango":("2026-03-01","2026-06-30")}
# brand-new items = very little history at the end of the year
NEW_ITEMS = {"Gourmet Truffle Burger":"2026-08-17","Suya Pizza":"2026-08-24","Kids Milkshake":"2026-09-05"}
# items launched somewhere inside the year
MID_LAUNCH = {"Breakfast Burrito":"2026-02-01","Avocado Toast":"2026-04-01","Mocha":"2026-03-15",
              "Shakshuka":"2026-01-20","Peppered Croaker":"2026-05-01","Fisherman Rice":"2026-04-15"}
DISCONTINUED = {"Concoction Rice":"2026-06-15","Seafood Chowder":"2026-07-01"}
# one item goes viral for a week right after launch (unexpected demand anomaly)
VIRAL = {"Suya Pizza":("2026-08-26","2026-09-01",6.0)}

# price shocks: (day index, % increase).  Price-sensitive items get 2 big increases
PRICE_SHOCKS = {
    "Chicken Shawarma Wrap":[(100,0.16),(230,0.14)],
    "Jollof Spaghetti":[(100,0.15),(230,0.15)],
    "Ice Cream Sundae":[(110,0.16),(240,0.14)],
    "Malt Drink":[(95,0.18),(225,0.12)],
    "Sweet Potato Fries":[(105,0.15),(235,0.15)],
    "Fried Plantain":[(100,0.17),(230,0.15)],
    "Double Cheeseburger":[(300,0.15)],       # loss makers are repriced very late
    "Beef Shawarma Wrap":[(300,0.14)],
    "Beef Steak":[(100,0.14)],"Grilled Salmon":[(110,0.12)],"Lamb Chops":[(105,0.13)],  # low sensitivity
}
# cost shocks only for loss makers: (day index, % increase of unit cost)
COST_SHOCKS = {"Double Cheeseburger":[(60,0.04),(140,0.05),(210,0.04)],
               "Beef Shawarma Wrap":[(60,0.04),(140,0.05),(210,0.04)]}

# --------------------------------------------------------------------------
# 4. LOCATIONS  id, area, city, state, region, traffic weight, opening date, seats, tier
# --------------------------------------------------------------------------
LOCATIONS = [
 ("L01","Lekki Phase 1","Lagos","Lagos","South West",1.5,"2022-03-10",90,"LARGE"),
 ("L02","Victoria Island","Lagos","Lagos","South West",1.7,"2021-06-01",120,"LARGE"),
 ("L03","Ikeja GRA","Lagos","Lagos","South West",1.4,"2021-09-15",100,"LARGE"),
 ("L04","Surulere","Lagos","Lagos","South West",1.0,"2022-08-20",70,"MEDIUM"),
 ("L05","Yaba","Lagos","Lagos","South West",1.1,"2022-01-12",75,"MEDIUM"),
 ("L06","Ajah","Lagos","Lagos","South West",1.1,"2023-02-03",65,"MEDIUM"),
 ("L07","Ikoyi","Lagos","Lagos","South West",1.2,"2021-11-05",80,"LARGE"),
 ("L08","Maryland","Lagos","Lagos","South West",1.1,"2022-10-18",85,"MEDIUM"),
 ("L09","Festac","Lagos","Lagos","South West",0.9,"2023-05-22",60,"MEDIUM"),
 ("L10","Magodo","Lagos","Lagos","South West",0.9,"2023-07-14",55,"SMALL"),
 ("L11","Ogudu","Lagos","Lagos","South West",0.8,"2023-09-09",50,"SMALL"),
 ("L12","Ikorodu","Lagos","Lagos","South West",0.8,"2024-01-20",55,"SMALL"),
 ("L13","Apapa","Lagos","Lagos","South West",0.8,"2022-12-01",60,"SMALL"),
 ("L14","Gbagada","Lagos","Lagos","South West",0.9,"2023-11-30",55,"SMALL"),
 ("L15","Ojodu Berger","Lagos","Lagos","South West",0.8,"2024-03-16",50,"SMALL"),
 ("L16","Wuse II","Abuja","FCT","North Central",1.3,"2022-04-25",95,"LARGE"),
 ("L17","Maitama","Abuja","FCT","North Central",1.3,"2022-07-08",100,"LARGE"),
 ("L18","Garki","Abuja","FCT","North Central",0.9,"2023-03-27",60,"MEDIUM"),
 ("L19","GRA Phase 2","Port Harcourt","Rivers","South South",1.1,"2022-11-14",80,"MEDIUM"),
 ("L20","Rumuola","Port Harcourt","Rivers","South South",0.8,"2023-08-05",55,"SMALL"),
 ("L21","Bodija","Ibadan","Oyo","South West",0.9,"2023-04-18",65,"MEDIUM"),
 ("L22","Independence Layout","Enugu","Enugu","South East",0.8,"2024-02-10",55,"SMALL"),
 ("L23","GRA Benin","Benin City","Edo","South South",0.8,"2024-05-06",55,"SMALL"),
 ("L24","Jabi Lake","Abuja","FCT","North Central",1.0,"2026-03-01",70,"MEDIUM"),   # NEW LOCATION
]
# location x item planted differences  ("default" = every other location)
PLANTED_LOC = {
 "Suya Platter":{"L16":3.0,"L17":3.0,"L18":2.4,"L24":2.5,"L19":0.6,"L20":0.6},
 "Pepper Soup Catfish":{"L19":4.0,"L20":3.5,"default":0.5},
 "Grilled Salmon":{"L02":2.5,"L07":2.8,"L17":2.5,"L12":0.4,"L09":0.5,"default":0.9},
 "Lamb Chops":{"L02":2.4,"L07":2.6,"L17":2.4,"L12":0.4,"L09":0.5,"default":0.9},
 "Ewa Agoyin":{"L04":3.0,"L05":2.5,"L09":2.2,"default":0.8},
 "Ofada Rice":{"L21":3.0,"L03":1.8},
}
CLOSURES = [("L07","2026-02-03","2026-02-09")]        # outage: location produces no sales
DECLINE_LOCATION = ("L12","2026-07-15",0.55)           # sales drop (competitor opens): share of orders lost
SPIKE_EVENT = ("L08","2026-05-23",180)                 # one-day event: extra orders
N_CATERING_ORDERS = 60                                 # abnormally high order values (corporate catering)
CATERING_LOCS = ["L02","L03","L16"]
MANUAL_DISCOUNT_LOC = ("L13",150)                      # unusual 60-90% discounts without a promotion

# --------------------------------------------------------------------------
# 5. PROMOTIONS
#   boost   : multiplier on the demand weight of in-scope items for promo orders
#   lift    : extra overall traffic during the promotion
#   cannibal: category -> multiplier (sales shifted away from a better product)
#   over    : wastage over-preparation factor for in-scope items while promo runs
#   chf     : channel -> multiplier (channel shift caused by the promotion)
#   tag     : GROUND TRUTH label (what the promotion "really" did)
# --------------------------------------------------------------------------
PROMOS = [
 dict(id="P001",name="Independence Day Treat",type="PERCENT_OFF",pct=0.10,start="2025-10-01",end="2025-10-03",
      days=None,scope="all",channels=None,new_only=False,loyal_only=False,boost=1.0,lift=0.15,redeem=0.25,broad=True,
      code="NAIJA65",tag="NEUTRAL"),
 dict(id="P002",name="Burger Bonanza 40% Off",type="CATEGORY_DISCOUNT",pct=0.40,start="2025-11-03",end="2025-11-16",
      days=None,scope=["C05"],channels=None,new_only=False,loyal_only=False,boost=5.0,lift=0.04,redeem=0.65,broad=True,
      cannibal={"C04":0.55,"C06":0.70},code="BURGER40",
      tag="TRAP_SALES_UP_PROFIT_DOWN_AND_CANNIBALISES_GRILLS"),
 dict(id="P003",name="Black Friday Feast",type="CATEGORY_DISCOUNT",pct=0.25,start="2025-11-24",end="2025-11-30",
      days=None,scope=["C04","C06","C08"],channels=None,new_only=False,loyal_only=False,boost=1.8,lift=0.35,redeem=0.45,
      broad=True,code="BF25",tag="GOOD_VOLUME_GAIN_NOTE_POST_PROMO_DIP_BASELINE"),
 dict(id="P004",name="Festive Season Combo",type="PERCENT_OFF",pct=0.15,start="2025-12-15",end="2026-01-02",
      days=None,scope="all",channels=None,new_only=False,loyal_only=False,boost=1.0,lift=0.12,redeem=0.30,broad=True,
      code="XMAS15",tag="NEUTRAL"),
 dict(id="P005",name="Healthy Start Brunch",type="CATEGORY_DISCOUNT",pct=0.20,start="2026-01-05",end="2026-01-25",
      days=None,scope=["C12"],channels=None,new_only=False,loyal_only=False,boost=3.5,lift=0.05,redeem=0.45,broad=False,
      code="BRUNCH20",tag="GOOD"),
 dict(id="P006",name="Valentine Dinner for Two",type="CATEGORY_DISCOUNT",pct=0.15,start="2026-02-10",end="2026-02-15",
      days=None,scope=["C06","C08"],channels=None,new_only=False,loyal_only=False,boost=1.6,lift=0.10,redeem=0.40,
      broad=False,code="LOVE15",tag="GOOD"),
 dict(id="P007",name="App Launch Offer 30% Off",type="PERCENT_OFF",pct=0.30,start="2026-03-01",end="2026-03-31",
      days=None,scope="all",channels=["WEBSITE_APP"],new_only=False,loyal_only=False,boost=1.0,lift=0.05,redeem=0.85,
      broad=True,code="APP30",tag="TRAP_CUSTOMERS_UP_MARGIN_COLLAPSES",chf={"WEBSITE_APP":4.0}),
 dict(id="P008",name="Easter Weekend Combo",type="CATEGORY_DISCOUNT",pct=0.15,start="2026-04-03",end="2026-04-06",
      days=None,scope=["C04","C03"],channels=None,new_only=False,loyal_only=False,boost=1.5,lift=0.20,redeem=0.40,
      broad=True,code="EASTER15",tag="GOOD"),
 dict(id="P009",name="Free Delivery Fortnight",type="FREE_DELIVERY",pct=0.0,start="2026-05-04",end="2026-05-17",
      days=None,scope=[],channels=["THIRD_PARTY_DELIVERY","WEBSITE_APP"],new_only=False,loyal_only=False,boost=1.0,
      lift=0.12,redeem=0.85,broad=False,code="FREEDEL",tag="NEUTRAL",
      chf={"THIRD_PARTY_DELIVERY":1.4,"WEBSITE_APP":1.2}),
 dict(id="P010",name="Wing Wednesday 25% Off Starters",type="CATEGORY_DISCOUNT",pct=0.25,start="2026-06-03",
      end="2026-08-26",days=[2],scope=["C01"],channels=None,new_only=False,loyal_only=False,boost=3.0,lift=0.05,
      redeem=0.50,broad=False,over={"C01":2.6},code="WINGS25",tag="TRAP_INCREASES_WASTAGE"),
 dict(id="P011",name="Democracy Day Mega Sale",type="PERCENT_OFF",pct=0.40,start="2026-06-12",end="2026-06-14",
      days=None,scope="all",channels=None,new_only=False,loyal_only=False,boost=1.0,lift=0.0,redeem=0.75,broad=True,
      code="DEMO35",tag="TRAP_SALES_UP_PROFIT_DOWN"),
 dict(id="P012",name="Rainy Day Soups",type="CATEGORY_DISCOUNT",pct=0.20,start="2026-07-01",end="2026-07-31",
      days=None,scope=["C02"],channels=None,new_only=False,loyal_only=False,boost=1.8,lift=0.04,redeem=0.40,broad=False,
      code="SOUP20",tag="GOOD"),
 dict(id="P013",name="Welcome 20 (first order)",type="NEW_CUSTOMER",pct=0.20,start="2025-10-01",end="2026-09-30",
      days=None,scope="all",channels=None,new_only=True,loyal_only=False,boost=1.0,lift=0.0,redeem=0.90,broad=False,
      code="WELCOME20",tag="ACQUISITION"),
 dict(id="P014",name="Loyalty Reward 10%",type="LOYALTY",pct=0.10,start="2025-10-01",end="2026-09-30",
      days=None,scope="all",channels=None,new_only=False,loyal_only=True,boost=1.0,lift=0.0,redeem=0.50,broad=False,
      code="LOYAL10",tag="LOW_INCREMENTAL_VALUE"),
 dict(id="P015",name="Dessert Duo 30% Off",type="CATEGORY_DISCOUNT",pct=0.30,start="2026-08-01",end="2026-08-31",
      days=None,scope=["C08"],channels=None,new_only=False,loyal_only=False,boost=2.4,lift=0.03,redeem=0.45,broad=False,
      code="DESSERT30",tag="GOOD_RAISES_BASKET_VALUE"),
 dict(id="P016",name="Pizza & Pasta Fridays",type="CATEGORY_DISCOUNT",pct=0.30,start="2026-01-02",end="2026-09-25",
      days=[4],scope=["C06"],channels=None,new_only=False,loyal_only=False,boost=3.5,lift=0.04,redeem=0.55,broad=False,
      code="FRIPIZZA",tag="CREATES_PROMO_DEPENDENT_ITEMS"),
 dict(id="P017",name="September Weekday Lunch",type="CATEGORY_DISCOUNT",pct=0.15,start="2026-09-01",end="2026-09-30",
      days=[0,1,2,3],scope=["C03","C05"],channels=None,new_only=False,loyal_only=False,boost=1.4,lift=0.05,redeem=0.35,
      broad=False,code="LUNCH15",tag="NEUTRAL"),
]
PROMO_CUSTOMER_BASE = 0.7      # promo-driven customers: weight on a normal day
PROMO_CUSTOMER_RESPONSE = 1.2  # extra weight while a big public promotion runs
PROMO_DEPENDENT_EXTRA = 4.0    # promo-dependent dishes react extra strongly to any promotion that covers them
POST_PROMO_DIP_DAYS = 21       # promo-driven customers go quiet after a big promotion
POST_PROMO_DIP = 0.55

# bundle / basket affinities (item A, item B, multiplier) - drives market-basket analysis
PAIRS = [
 ("Jollof Rice","Fried Plantain",10),("Jollof Rice","Grilled Chicken Half",6),("Fried Rice","Fried Plantain",6),
 ("Fried Rice","Grilled Chicken Half",5),("Classic Beef Burger","French Fries",8),("Classic Beef Burger","Cola 50cl",6),
 ("Double Cheeseburger","French Fries",8),("Chicken Burger","French Fries",6),("French Fries","Cola 50cl",4),
 ("Pepperoni Pizza","Cola 50cl",5),("Margherita Pizza","Garden Salad",3),("Egusi Soup","Pounded Yam",14),
 ("Ogbono Soup","Pounded Yam",14),("Efo Riro","Eba",12),("Okra Soup","Eba",10),("Suya Platter","Chapman",5),
 ("Chicken Wings","Chapman",4),("Cheesecake","Cappuccino",6),("Tiramisu","Espresso",6),
 ("Chocolate Lava Cake","Latte",5),("Peppered Snail","Zobo",5),("Kids Chicken Nuggets","Kids Milkshake",8),
 ("Kids Mini Burger","Kids Fries Combo",6),("Pancake Stack","Latte",6),("Full English Breakfast","Americano",6),
 ("BBQ Ribs","Coleslaw",8),("Mixed Grill Platter","Sweet Potato Fries",6),("Asun Peppered Goat","Chapman",5),
 ("Spaghetti Bolognese","Garlic Bread",5),("Pepper Soup Goat","Boli & Fish",3),("Ofada Rice","Zobo",4),
]

# --------------------------------------------------------------------------
# 6. CUSTOMERS
# --------------------------------------------------------------------------
ARCHETYPES = ["LOYAL","FREQUENT","PROMO_DRIVEN","OCCASIONAL","NEW","CHURNED","AT_RISK"]
ARCH_SHARE = [0.06,0.12,0.15,0.33,0.12,0.12,0.10]
ARCH_MEAN_ORDERS = [22,10,7,2.2,3.0,14,9]   # per active year (NEW = whole window)
GUEST_SHARE = 0.12                            # orders without a customer id
# channel probabilities per archetype (+ guest row): DINE_IN, TAKEAWAY, WEBSITE_APP, THIRD_PARTY_DELIVERY
CHANNELS = ["DINE_IN","TAKEAWAY","WEBSITE_APP","THIRD_PARTY_DELIVERY"]
CHANNEL_P = [
 [0.55,0.13,0.22,0.10],   # LOYAL
 [0.45,0.17,0.20,0.18],   # FREQUENT
 [0.25,0.12,0.30,0.33],   # PROMO_DRIVEN
 [0.45,0.20,0.14,0.21],   # OCCASIONAL
 [0.35,0.15,0.25,0.25],   # NEW
 [0.42,0.20,0.16,0.22],   # CHURNED
 [0.40,0.18,0.20,0.22],   # AT_RISK
 [0.50,0.30,0.00,0.20],   # GUEST
]

# --------------------------------------------------------------------------
# 7. TIME PATTERNS
# --------------------------------------------------------------------------
DOW_MULT = [0.85,0.85,0.90,0.95,1.25,1.45,1.20]                # Mon..Sun
MONTH_MULT = [0.90,0.95,1.00,1.05,1.00,0.95,0.92,0.95,1.00,1.00,0.95,1.30]   # Jan..Dec
GROWTH = 0.10                                                  # +10% over the year
HOLIDAYS = {"2025-10-01":1.25,"2025-12-24":1.20,"2025-12-25":1.35,"2025-12-26":1.30,"2025-12-31":1.40,
            "2026-01-01":1.25,"2026-02-14":1.35,"2026-04-03":1.15,"2026-04-05":1.20,"2026-05-01":1.10,
            "2026-06-12":1.20}
HOURS = list(range(7,23))
HOUR_W_WEEKDAY = [3,5,5,4,7,12,14,9,5,4,6,11,15,14,9,4]
HOUR_W_WEEKEND = [1,3,5,8,10,12,13,11,8,6,7,11,14,15,11,6]
ONLINE_HOUR_TILT = [0.5,0.5,0.6,0.7,0.9,1.0,1.0,0.9,0.9,1.0,1.2,1.4,1.5,1.5,1.3,1.0]
# hour groups: 0 breakfast(7-10) 1 lunch(11-14) 2 afternoon(15-17) 3 dinner(18-22)
HOURGROUP_MULT = {   # category -> multiplier per hour group
 "C12":[8.0,0.8,0.15,0.1],"C10":[3.0,1.0,1.4,0.8],"C04":[0.4,1.0,1.0,1.6],"C05":[0.4,1.2,1.1,1.0],
 "C06":[0.3,0.9,1.1,1.5],"C08":[0.5,0.8,1.2,1.3],"C02":[0.3,1.2,1.0,1.2],"C03":[0.3,1.4,1.0,1.0],
 "C09":[0.8,1.0,1.2,1.1],"C01":[0.3,0.9,1.0,1.4],
}

QTY_P = [0.78,0.15,0.04,0.02,0.01]

# --------------------------------------------------------------------------
# 8. DATA QUALITY - how dirty should the RAW data be?  (rates are fractions)
# --------------------------------------------------------------------------
DIRTY = dict(
    status_cancelled=0.030, status_refunded=0.009, status_void=0.006,
    payment_null=0.020, customer_age_null=0.040,
    dup_order_exact=0.004, dup_line_exact=0.003, dup_order_near=0.001, dup_customer=0.002,
    line_qty_invalid=0.0005, line_item_null=0.001, line_item_unknown=0.001,
    line_price_invalid=0.0004, line_price_extreme=0.0002, line_discount_wrong=0.0005,
    order_date_invalid=0.0005, order_loc_invalid=0.001, order_loc_null=0.0005,
    rating_invalid=0.002, wastage_impossible=0.0005, wastage_unit_kg=0.020, wastage_unit_g=0.010,
    wastage_unit_pcs=0.040, wastage_unit_case=0.020, wastage_loc_invalid=0.0005, wastage_item_null=0.0005,
    inventory_neg=0.0005, inventory_loc_invalid=0.0005, price_invalid_rows=6,
)
