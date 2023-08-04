# Event-Management-API

## Description
This is a Flask-based application that uses Auth0 for user login verification. 
It allows users to register, login, and manage events and coordinators. 
The application verifies JWT (JSON Web Tokens) to ensure users can only access or modify event/coordinator information they own.
Users can register, login, and access the API endpoints through Postman.

## Usage
- Register: Create a new account by visiting the registration page and providing your details.

- Login: Log in using your credentials to obtain an access token.

- API Access: With the access token, you can make API requests to add new users, events, and coordinators.
- Testing: Postman test suite and environment files have been provided.

## Endpoints
- POST /users: Add a new user to the system.

- POST /events: Add a new event to the system (User authentication required).

- GET /events/:id: Retrieve a specific event by ID (User authentication required).

- PATCH /events/:id: Update an existing event (User authentication required).

- DELETE /events/:id: Delete an event by ID (User authentication required).

- POST /coordinators: Add a new coordinator to the system (User authentication required).

- GET /coordinators/:id: Retrieve a specific coordinator by ID (User authentication required).

- PATCH /coordinators/:id: Update an existing coordinator (User authentication required).

- DELETE /coordinators/:id: Delete a coordinator by ID (User authentication required).

## Authentication
This application uses Auth0 for user authentication and authorization. Users must log in to obtain a JWT (JSON Web Token) access token, which is used for authorization when accessing API endpoints. The access token is verified to ensure users can only access/modify their own information.
