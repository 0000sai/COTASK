# TutorialShopAPI

TutorialShopAPI is a RESTful API project built using Express and integrated with MongoDB. It serves as the backend for the TutorialShop web application, providing endpoints for managing tutorials, courses, users, and handling authentication and authorization. This README file provides an overview of the project, installation instructions, usage guidelines, contribution guidelines, and additional resources.

## Table of Contents

- [TutorialShopAPI](#tutorialshopapi)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Features](#features)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Endpoints](#endpoints)
  - [Contributing](#contributing)
  - [License](#license)
  - [Additional Resources](#additional-resources)
  - [Contact](#contact)

## Overview

TutorialShopAPI is a Node.js-based RESTful API designed to handle CRUD operations for tutorials, courses, and user management. It utilizes Express.js as the web application framework and integrates with MongoDB as the database for storing data. The API supports user authentication and authorization using JSON Web Tokens (JWT) for secure access to resources.

## Features

- CRUD operations for tutorials, courses, and users.
- User authentication and authorization using JWT.
- Secure password hashing for user authentication.
- Middleware for handling request validation and error handling.
- Integration with MongoDB for data storage.
- CORS support for cross-origin requests.

## Installation

To run TutorialShopAPI locally, follow these steps:

1. Clone the repository:

   ```bash
   git clone git@gitlab.com:dotcom-group/devops-group/devops-engineers-2023/davscot24group/dav-e2e-application-repo.git
   ```

2. Navigate to the project directory:

   ```bash
   cd tutorial-service
   ```

3. Install dependencies using npm:

   ```bash
   npm install
   ```

4. Set up environment variables:

   Create a `.env` file in the root directory of the project and add the following variables:

   ```sh
   PORT=8080
   MONGODB_URI=mongodb+srv://<username:password>@cen-idea-data.8bmco.mongodb.net/<db_name>?retryWrites=true&w=majority
   ```

   Replace `<port_number>` with the desired port for running the server, `<mongodb_uri>` with the MongoDB connection URI.

5. Start the server:

   ```sh
   npm run start:api
   ```

   This will start the server on the specified port.

## Usage

Once the server is running, you can send HTTP requests to the defined endpoints to interact with the API. Ensure that you have proper authentication tokens for accessing protected endpoints. Refer to the API documentation for details on available endpoints and request/response formats.

## Endpoints

Below are some of the main endpoints provided by TutorialShopAPI:

- `POST /api/tutorials/auth/register`: Register a new user.
- `POST /api/tutorials/auth/login`: Authenticate user and generate JWT token.
- `GET /api/tutorials/tutorials`: Get all tutorials.
- `GET /api/tutorials/tutorials/:id`: Get a specific tutorial by ID.
- `POST /api/tutorials/tutorials`: Create a new tutorial.
- `PUT /api/tutorials/tutorials/:id`: Update a tutorial by ID.
- `DELETE /api/tutorials/tutorials/:id`: Delete a tutorial by ID.
- Other endpoints for courses, users, etc.

## Contributing

We welcome contributions from the community. To contribute to this project, follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and ensure the code follows the project's coding standards.
4. Write tests if necessary.
5. Commit your changes with descriptive commit messages.
6. Push your changes to your fork.
7. Submit a pull request to the main repository.

Please ensure your pull request description clearly describes the changes you've made and the problem it solves.

## License

MIT licensed

## Additional Resources

- [API Documentation] - Add link to API documentation.
- [Postman Collection] - Provide a link to a Postman collection for testing endpoints.
- [TutorialShopAPI Repository] - Link to the repository of TutorialShopAPI.
- [TutorialShop Web Application] - Link to the TutorialShop web application repository or demo.

## Contact

If you have any questions or concerns, feel free to contact the project maintainer(s) at <edwin.nwofor@yahoo.com>.
