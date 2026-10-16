## Starting the container  
- Before attempting to start the container make sure you have created and filled in a .env file based on .env.example  
- To start the containerized environment navigate to the project root in the terminal or cmd and run: `docker compose up`  
- If you have installed new dependencies or made changes to the Dockerfile you want to build the container from scratch. Run: `docker compose up --build`  
- If you want to run the container in the background so it doesn't busy the terminal run: `docker compose up -d`  
	- if you run it this way you can view the logs by running: `docker logs -f`  
- Check if the containers are running run: `docker ps` You should see two containers running:  
	- `encore_postgres` for the database  
	- `encore_backend` for the backend server  

## Stopping the container  
- To stop the container without clearnign any volumnes run: `docker compose down`  
- If you want to delete all container data, including the database volumes run: `docker compose down -v`  

## Running commands inside the backend container  
- To step inside the container run: `docker compose exec backend bash`  
- To leave the container run: `exit`  
- To run a command inside the container without stepping into it run: `docker compose exec backend [your command]`  

## Running commands inside the database container  
- To step inside the container run: `docker compose exec postgres_db bash`  
- To leave the container run: `exit`  
- To run a command inside the container without stepping into it run: `docker compose exec potgres_db [your command]`  

## Accessing the database directly  
- To enter the database run: `docker compose exec postgres_db psql -U encore_db_user -d encore_db`  
- You can then give the database instructions directly with postgresql commands. (see database.md)  
- To exit the database run: `\q`  
