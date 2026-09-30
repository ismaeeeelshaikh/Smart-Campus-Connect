# how to run this project
# and python version above 3.10 

# for backend
1. cd backend
2. python -m venv venv
3. venv\Scripts\activate
4. uvicorn app.main:app --reload

# for frontend
1. cd frontend
2. npm install
3. npm run dev

# For resetting knowledge base, we need to use -> when we add new data after adding just make sure to fire this command
del vectorstore.pkl

# after running above command again run backend server so that updated data should be fetched
