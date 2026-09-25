# Decision Book

## Part 1: Data Management

For the schema design, I split the data into primary two tables to avoid potential redundancy issues. 

Each subject is associated with three samples, so it is best practice to have the samples in a separate table and have them point to the associated subject.

I considered splitting project into a separate table, but I decided it was too early for that given the lack of metadata.

I also considered splitting each of the sample cell counts into a separate table, but it also seemed early for this given only having five counts.

I considered splitting enum types like condition into separate tables, but this would introduce more joins, and with a relatively small dataset like this one, I decided that would not be worth it. 

I considered adding an enrollment table with subject, project, treatment, and response, but since all subjects only have one treatment in this data, I kept it simple and skipped this.

I opted to convert values like subject from strings to numbers, since this would save space and avoid unexpected behaviors with queries.