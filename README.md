- after cloning the repository, create a .env file with following keys and values:
	- SECRET_KEY=<your_secret_key>
	- ACCESS_TOKEN_EXPIRE_MINUTES=30
	- DATABASE_URL=sqlite:///./hiper.db

- run the app using:

**uvicorn app.main:app --reload --port 8005 --host 0.0.0.0**

(port and host flags are not compulsary)
- ***_needs further debugging_***
