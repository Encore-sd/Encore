## Project Specific Database Information  

### users  
- collumns  
	- userid SERIAL	:	primary_Key  
	- firstname VARCHAR(100)  
	- lastname VARCHAR(100)  
	- email VARCHAR(255)  
	- password VARCHAR(255)  
	- token VARCHAR(255)  
	- tokenexpiredate TIMESTAMP  

### memories
- collumns  
	- memoryid SERIAL	:	PRIMARY KEY  
	- userid INT NOT NULL	:	foreign_key  
	- audiotranscription TEXT  
	- audiofilelocation VARCHAR(500)  
	- imagefilelocation VARCHAR(500)  
	- keywords TEXT  
	- gpslongitude NUMERIC(11, 8)  
	- gpslatitude NUMERIC(10, 8)  
	- timecaptured TIMESTAMP  


## General Database Information

The database uses postgreSQL

When the container is started (see docker.md) it will automatically runall sql files at /backend/db/*.sql in alphapetical order; which will set up the following tables in the encore_db, based on the ERDs.  
- users  
- memories  

Once you have entered the database (see docker.md) the following commands will be helpful:  
- `\list` : List all of the databases in the container (equivilant mysql: SHOW DATABASES)  
- `\connect db_name` : Connect to a database. (equivilant mysql: USE db_name)  
- `\d` : See all the tables in a database. (equivilant mysql: SHOW TABLES)  
- `\d table_name` : show all the column names in a table. (equivilant mysql: DESCRIBE table_name)  

### Creating a new table  
- You can mosty use mysql commands, but instead of AUTO_INCREMENT use: SERIAL  
- Creating a table example:  
	CREATE TABLE users (  
    	id SERIAL PRIMARY KEY,  
	    username VARCHAR(50) NOT NULL UNIQUE,  
    	email VARCHAR(100) NOT NULL UNIQUE,  
	    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
	);  

### Adding indexes to a table  
- Create an index on a signle column by onlypassing that column name. Or, create a composite index by passing multiple column names.  
	- `CREATE INDEX index_name ON table_name ([column1_name, column2_name, . . .])`  

### Delete a table  
- DROP TABLE table_name  

### Adding a column to an existing table  
- ALTER TABLE table_name ADD COLUMN column_name data_type constraints;  
- datatypes  
	- VARCHAR(size)	:	A String of some max size  
	- BOOLEAN	:	A true/false value  
	- INT	:	An integer number  
	- DATE	:	A date
	- TIMESTAMP	:	A date and time

### Deleting a column  
- ALTER TABLE table_name DROP COLUMN column_name;  

### Running a sql file to seed or otherwise alter the database  
- From the terminal run: `docker compose exec -T postgres_db psql -U encore_db_user -d senior encore_db < [path to sql file]`  

### Common sql commands
- Insert a row	:	`INSERT INTO table_name ([column_names . . .]) VALUES ([values . . .]);`  
- sql search	:	`SELECT [column names * for all] FROM table_name WHERE [some condition: column name = value];`  
- count the number of results	: `SELECT COUNT(*) FROM users;`  
