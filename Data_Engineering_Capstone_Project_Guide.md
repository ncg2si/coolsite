# `Data Engineering Capstone Project Guide`

## `From raw data to a reliable data product`

### `Your challenge`

Your capstone project is an opportunity to demonstrate that you can take a real-world data problem and build a reliable, well-documented data solution.

You will choose your own topic, identify a potential end user, find your own data, and decide how to build your solution.

The goal is not simply to create a pipeline that works once. It is to demonstrate that you can make sound engineering decisions, build a reproducible data workflow, and deliver trustworthy data that someone else can use.

Your project should demonstrate the technical skills and engineering judgement expected of a junior data engineer entering the job market.

You have the freedom to choose your topic, data sources, technologies, and how your solution develops. However, there are some core engineering capabilities that every successful project must demonstrate.

### `1. What are you expected to build?`

You will build an end-to-end data engineering solution that transforms source data into a useful data product.

Your project should include:

* A clearly defined problem, business or analytical objective, and intended end user.  
* Suitable datasets, with an explanation of why you selected them.  
* A documented data catalog and dataset assessment.  
* A documented architecture and data model.  
* A reproducible ingestion and transformation pipeline.  
* Appropriate storage and data quality controls.  
* Incremental processing where appropriate.  
* Logging, error handling, and pipeline recovery mechanisms.  
* A curated dataset or analytical output that serves your chosen use case.  
* Documentation explaining how your solution works and how to run it.

For example, you might build a pipeline that collects sales data, transforms it into analytical tables, and makes those tables available for a sales dashboard.

You are not required to build a sophisticated dashboard. A well-designed and documented set of analytical tables can be a successful data product in its own right.

Your focus should be on the quality, reliability, and maintainability of the data engineering solution.

### `2. Start with a problem, not a technology`

Before choosing your tools, think about what you want to achieve.

Ask yourself:

* What question am I trying to answer?  
* Who would benefit from the answer?  
* What information would that person need?  
* What data would help me provide that information?  
* How would the end user consume or interact with the resulting data product?

Your end user might be a sales manager, a logistics team, a financial analyst, a researcher, or another person in an organisation or an entirely different organisation.

Think about the requirements of your intended user. What information do they need? What decisions could they make using your data product?

You have the freedom to choose your own topic and let your project develop as you learn more about the data. However, you should be able to explain the problem you are solving and why the resulting data product is useful.

Remember that your pipeline and data model should ultimately serve the needs of your intended end user.

### `3. Find and assess your data`

Finding a dataset is one of the most important parts of your project.

A dataset can look interesting but still be unsuitable for your intended use case. Before committing to a source, you should investigate whether it contains the information you need, whether you can access it reliably, and whether it is feasible to work with within the time available.

#### Your dataset assessment

You should investigate at least two candidate datasets before making your final selection.

For each candidate, document the following:

| Assessment area | Questions to investigate |
| :---- | :---- |
| Source and access | Where does the data come from? Can you access it legally and reliably? Are there API limits or access restrictions? |
| Structure | What does each row represent? What are the important fields and data types? |
| Data quality | Are there missing values, duplicates, inconsistent formats, or other issues? |
| Updates and history | How frequently is the data updated? Is historical data available? Can you identify new or changed records? |
| Suitability | Can the data answer your intended question? What information is missing? |
| Feasibility | Can you realistically complete the project with this data and your available time? |
| Governance | Does the data contain personal or sensitive information? Are there restrictions on its use, storage, or sharing? |
| Reliability | Is the source stable? What happens if it becomes unavailable or changes its structure? |

You should also identify any assumptions or limitations that could affect your project.

#### Your data catalog

Create a lightweight data catalog for your selected source.

This should describe:

* The source and where the data originates.  
* The meaning of the dataset and what each row represents.  
* The available fields, their definitions, and data types.  
* Potential primary keys and relationships.  
* Known data quality issues.  
* Update frequency and historical availability.  
* Any relevant access, usage, or governance restrictions.

Your data catalog should help you understand the data and make informed decisions about how to model and transform it.

You do not need to build a cataloguing platform. A documented spreadsheet, Markdown file, or equivalent format is sufficient.

#### Your decision

After assessing your candidate datasets, select the one you believe is most suitable.

You should present both candidates, identifying one as your preferred dataset (hero candidate) and the other as a fallback.

Explain why you selected your preferred dataset, what limitations you identified, and what you might need to do to make the data usable.

You are not expected to find a perfect dataset. Identifying and managing the limitations of real-world data is part of the engineering challenge.

### `4. Design your solution`

Once you have selected your data, plan how you will turn it into a useful data product.

Your architecture should explain:

* How data will be extracted from its source.  
* Where the data will be stored.  
* How the data will be validated and transformed.  
* How the different stages of your pipeline relate to one another.  
* Where the final data product will be made available.  
* How your pipeline will be executed and monitored.  
* What happens when something goes wrong and how you will recover.

You should also define your data model, including the purpose of your tables, their grain, and the relationships between them.

Think about how your solution might evolve if the amount of data or the number of users increased.

#### Storage and architecture

There is no single architecture that every project must follow.

You might use a relational database, a data warehouse, a data lake, a NoSQL database, or a combination of approaches.

You may choose to implement a medallion architecture with bronze, silver, and gold layers, or use another structure that better suits your project.

The important thing is that you can explain why you chose your approach and what trade-offs you considered.

For example:

* Why did you choose a particular storage technology?  
* Why are you separating raw and transformed data?  
* Would a relational database be sufficient, or is another storage approach more appropriate?  
* What are the implications for performance, scalability, and cost?  
* How would your architecture change if your data volume increased?

You do not need to build a large-scale system. You should be able to explain how your architecture could evolve as requirements change.

### `5. Build your pipeline`

Your pipeline should take data from its source, process it, and make it available for use.

You have flexibility in how you implement it, but your solution should demonstrate the following capabilities.

Ingestion and storage

Your pipeline should:

* Extract data from your chosen source.  
* Store the data in an appropriate format and location.  
* Make the ingestion process reproducible.  
* Handle repeated runs without creating unnecessary duplicates or losing previously processed data.  
* Record enough information to understand what happened during each run.

You should be able to explain why you chose your storage approach and how it supports your use case.

Where appropriate, preserve the original source data so that you can reprocess it if your transformation logic changes.

Incremental processing

Where your source supports it, implement a strategy for processing new or changed data without unnecessarily reprocessing the entire dataset.

For example, you might use a timestamp, sequence number, or source-provided change indicator to identify new or updated records.

You should demonstrate that your pipeline can:

* Identify data that has already been processed.  
* Process new or changed records.  
* Handle records that are updated after their initial ingestion.  
* Avoid introducing duplicate records when the pipeline is run again.  
* Recover safely if a processing run fails partway through.

You should also consider how your pipeline tracks its processing progress, for example through a watermark or another appropriate mechanism.

If incremental processing is not appropriate for your source, explain why and demonstrate an alternative approach that supports repeatable processing.

You are not required to implement complex change data capture (CDC), streaming, or distributed processing.

Transformation and data modelling

Transform your source data into a structure that is useful for your intended end user.

This may include cleaning, joining, filtering, aggregating, or enriching the data.

Your final tables should have a clear purpose and be designed around the questions your end user needs to answer.

You should be able to explain:

* What each table represents.  
* The grain of each table.  
* How tables relate to one another.  
* Why the model is suitable for the intended use case.  
* How your transformations improve the usability and consistency of the data.

You may use tools such as SQL, Python, or dbt, depending on your chosen architecture and the requirements of your project.

The emphasis is on sound modelling and transformation decisions rather than the use of a particular tool.

Data quality and error handling

Your pipeline should include appropriate checks to identify data quality issues.

Consider:

* Missing or invalid values.  
* Duplicate records.  
* Unexpected data types or formats.  
* Invalid relationships between tables.  
* Records that do not meet the requirements of your intended data product.  
* Unexpected changes to the source data structure.

Implement meaningful tests that demonstrate whether your data meets the requirements you have defined.

You should also demonstrate what happens when something goes wrong.

For example, you might quarantine invalid records for further investigation rather than allowing them to enter your final analytical tables.

Where appropriate, implement retries or other mechanisms to handle temporary failures.

You should be able to explain how failures are identified, how problematic records are handled, and how the pipeline can recover without compromising the integrity of your data.

Your approach should be appropriate to your source and the risks associated with your data.

Logging and pipeline observability

A data pipeline should not be a black box. Another person should be able to understand whether it ran successfully, what it processed, and what went wrong if it failed.

Implement appropriate logging so that your pipeline provides information such as:

* When a pipeline run started and finished.  
* Which processing stage was running.  
* How many records were extracted, processed, rejected, or written.  
* Whether the run succeeded or failed.  
* What error occurred when something went wrong.

Your logs should provide enough information to help identify and troubleshoot problems without exposing sensitive information or credentials.

You do not need a full monitoring platform. Basic logging in your chosen language or tool is sufficient.

You should also demonstrate how you would identify a failed pipeline run and investigate the cause.

Testing and version control

Your project should demonstrate basic software engineering practices.

You should:

* Use Git to manage and version your code.  
* Organise your code into understandable and maintainable components.  
* Implement tests for important transformations and data quality requirements.  
* Ensure that your pipeline can be executed using documented instructions.  
* Avoid hardcoding environment-specific settings or credentials into your code.

You do not need an elaborate testing framework or an advanced branching strategy. The goal is to demonstrate that you understand how to develop, test, and maintain a data solution that another engineer can work with.

### `6. Data governance and responsible data handling`

Data engineering is not just about moving and transforming data. You must also understand the responsibilities associated with working with it.

Consider the following:

* Where does your data originate, and who is responsible for it?  
* Is the data publicly available, or do you have permission to use it?  
* Does it contain personal, sensitive, or confidential information?  
* Are there restrictions on how the data can be stored, processed, or shared?  
* Who should have access to the data?  
* How long should the data be retained, where relevant?  
* Are there any data protection or privacy considerations?

If your project involves personal data, you should be aware of relevant data protection requirements, including the principles of the General Data Protection Regulation (GDPR).

You are not expected to become a data protection specialist. However, you should recognise that data has ownership, usage restrictions, and responsibilities attached to it.

Security and credentials

If your project requires credentials, API tokens, or other secrets, demonstrate an appropriate method of storing and accessing them securely.

For example:

* Do not commit API keys, passwords, or other credentials to Git.  
* Use environment variables or an appropriate secrets management mechanism.  
* Keep sensitive configuration separate from your source code.  
* Avoid exposing credentials in logs or documentation.

If you use GitHub, you may explore GitHub Actions secrets or other appropriate mechanisms.

The important thing is that you understand the risks and handle credentials responsibly.

### `7. Make your data product useful`

Your final output should provide something meaningful to your intended end user.

This might be a set of analytical tables, a data mart, a report, a dashboard, or another suitable output.

For example, if your project is intended to support sales analysis, you might create tables that allow users to investigate sales performance by product, region, or time period.

Your final data product should be documented so that another person can understand:

* What the data represents.  
* How it was produced.  
* What each table or field means.  
* What assumptions or limitations apply.  
* How the data should be used.

A dashboard is optional. If you have time to build one, it should demonstrate the value of your data product rather than become the main focus of your engineering work.

### `8. Minimum project requirements`

Every capstone project must demonstrate the following capabilities.

| Capability | Expected evidence |
| :---- | :---- |
| Problem definition | A defined problem, intended end user, and project objective. |
| Data suitability | An assessment of at least two candidate datasets and a documented selection decision. |
| Data catalog | A description of the source, fields, structure, relationships, and known limitations. |
| Architecture | An architecture diagram and justification of key engineering decisions. |
| Data modelling | A documented data model with clear table purposes, grain, and relationships. |
| Ingestion and storage | A reproducible pipeline and an appropriate storage strategy. |
| Incremental processing | A suitable approach for handling new or changed data, or a justified alternative. |
| Logging | Sufficient logging to understand pipeline runs and investigate failures. |
| Data quality | Meaningful checks and tests that demonstrate whether the data is fit for purpose. |
| Error handling | An appropriate failure-handling and recovery approach, including a demonstrated failure scenario. |
| Version control | Code managed through Git, with clear setup and execution instructions. |
| Governance and security | Appropriate consideration of data usage, privacy, access, and credential handling. |
| Data product | A curated dataset or analytical output that serves the intended use case. |
| Documentation | Instructions explaining how to set up, run, and understand the project. |
| Demonstration | A working solution that you can explain and demonstrate. |

These requirements form the minimum expected outcome.

The implementation should be appropriate to the size and complexity of your project. You are not expected to build an enterprise-scale platform, but you should be able to explain and demonstrate the underlying engineering principles.

### `9. Optional extensions`

Once you have completed the minimum requirements, you can consider extending your project.

Choose extensions that add value to your solution and that you can explain confidently.

| Extension | What you could demonstrate |
| :---- | :---- |
| dbt | Modular transformations, data testing, documentation, and lineage. |
| CI/CD | Automated testing, validation, and deployment through a workflow such as GitHub Actions. |
| Infrastructure as Code | Reproducible infrastructure using tools such as Terraform. |
| Advanced monitoring | Metrics, alerts, and more detailed operational visibility. |
| Cloud deployment | Deploying your solution to an appropriate cloud environment. |
| Distributed processing | Processing larger datasets using an appropriate distributed approach. |
| Advanced orchestration | Scheduling and managing more complex pipeline dependencies. |
| Dashboard | Making your data product accessible to an end user. |

These extensions are not required for a successful capstone.

Choose extensions that are relevant to your architecture and use case. A well-engineered, complete project is more valuable than an ambitious project that remains unfinished.

### `10. Your project documentation`

Your final project should include documentation that allows another person to understand and reproduce your work.

At a minimum, your documentation should cover:

1. Project overview: The problem, intended end user, and purpose of the data product.  
2. Dataset assessment: Your candidate data sources, the selection rationale, and their limitations.  
3. Data catalog: The source structure, field definitions, relationships, and known quality issues.  
4. Governance: Relevant usage restrictions, privacy considerations, and security decisions.  
5. Architecture: A diagram and explanation of the data flow, storage, and key design decisions.  
6. Data model: The purpose of your tables, their grain, and important relationships.  
7. Pipeline implementation: How the pipeline works and how to run it.  
8. Incremental processing: How new or changed data is identified and processed.  
9. Reliability: How logging, testing, error handling, and recovery are implemented.  
10. Results: What your data product provides and how it supports the intended use case.  
11. Future improvements: What you would change or improve if you had more time or resources.

You should also include any necessary setup instructions, dependencies, environment configuration, and a clear description of the tools and technologies used.

Another engineer should be able to read your documentation, understand your solution, and reproduce the pipeline without having to guess how it works.

## `Your capstone, your engineering decisions`

You have the freedom to choose your own topic, data, tools, and approach.

Use that freedom to build something meaningful. Start with a problem, assess your data carefully, make deliberate engineering decisions, and focus on delivering a reliable data product.

A successful capstone is not the project with the most technology or the biggest dashboard.

It is the project that demonstrates you can take data from its source, turn it into something trustworthy and useful, and explain how you built it.

That is the foundation of good data engineering.

