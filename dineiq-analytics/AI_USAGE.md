# AI Usage Declaration (template - complete it yourself)

The SRS (section 1.8 and deliverable 16) requires every AI tool used during development to be declared, and every AI-generated
piece of code to be reviewed, modified where needed, understood and tested by a team member.

| Field | Entry |
|---|---|
| Tool name | Claude (Anthropic) |
| Purpose | Design help and first drafts of: Phase 1 dataset generator, validator, Parquet converter; Phase 2 Spark ingestion, data-quality and cleaning jobs, Phase 3 Spark SQL integration and feature engineering, Phase 4a analytics jobs (menu, customers, baskets, pricing, promotions, anomalies), and their tests |
| Type of assistance | Code generation, schema design, documentation drafting |
| Files / modules affected | data_generator/*, spark_jobs/*, spark_sql/*, tests/*, run_all.sh/bat, documentation/* |
| Modifications performed | (write what YOU changed, e.g. "changed promo P002 discount to 35%, added location L25") |
| Testing completed | Ran generator at scale 0.05 and 1.0, ran validate_dataset.py; ran the three Spark jobs at full scale; tests/test_phase2_cleaning.py 53/53 and tests/test_phase3_features.py 42/42 and tests/test_phase4_analytics.py 59/59 passed, (add your own tests) |
| Team member who verified the output | (your name) |

Add one row per tool and per new module as the project grows (Phase 2 Spark scripts, models, dashboards).
Final analytics, predictions and recommendations must come from your own Spark / Python logic, not from an external AI decision API.
