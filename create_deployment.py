from prefect import flow

# Source for the code to deploy (here, a GitHub repo)
SOURCE_REPO="https://github.com/elias-dzobo/personalised-ml-papers"

if __name__ == "__main__":
    flow.from_source(
        source=SOURCE_REPO,
        entrypoint="data_ingestion_pipeline.py:pipeline", # Specific flow to run
    ).deploy(
        name="ml-papers-deployment",
        # parameters={
        #     "github_repos": [
        #         "PrefectHQ/prefect",
        #         "pydantic/pydantic",
        #         "huggingface/transformers"
        #     ]
        # },
        work_pool_name="ml-papers-pool",
        cron="0 0 * * *",  # Run every hour
    )