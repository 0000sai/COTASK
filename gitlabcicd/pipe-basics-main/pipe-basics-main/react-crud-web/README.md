# TutorialShop

TutorialShop is a web application built using React and integrated with a REST API and MongoDB. It serves as a platform for tutorials and online courses, allowing users to browse, purchase, and consume educational content. This README file provides an overview of the project, installation instructions, usage guidelines, contribution guidelines, and additional resources.

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Table of Contents

- [TutorialShop](#tutorialshop)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Features](#features)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Contributing](#contributing)
  - [License](#license)
  - [Contact](#contact)

## Overview

TutorialShop is a full-stack web application designed to provide users with access to a wide range of tutorials and online courses. It leverages React for the front-end development, integrating with a RESTful API built using technologies like Node.js and Express.js for the backend. MongoDB is utilized as the database to store user data, tutorials, and course information.

## Features

- User authentication and authorization.
- Browse tutorials and courses by category.
- Search functionality to find specific tutorials or courses.
- User profile management.
- Shopping cart for purchasing courses.
- Integration with payment gateways for secure transactions.
- Admin panel for managing tutorials, courses, and users.
- Responsive design for seamless user experience across devices.

## Installation

To run TutorialShop locally, follow these steps:

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

   OR

   ```bash
    yarn install

   ```

4. Set up environment variables:

   Create a `.env` file in the root directory of the project and add the following variables:

   ```sh
   REACT_APP_API_ADDRESS=<api_base_url>
   PORT=8081
   ```

   Replace `<api_address>` with the URL of your REST API.

5. Start the development server:

    ```sh
    export REACT_APP_API_ADDRESS=http://127.0.0.1:8080/api
    npm run start:ui
    ```

    OR

    ```sh
    export REACT_APP_API_ADDRESS=http://127.0.0.1:8080/api
    yarn start:ui
    ```

    Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

    The page will reload if you make edits.

## Usage

Once the application is running locally, you can access it via the browser. Use the provided navigation to browse tutorials and courses, search for specific content, manage your user profile, and add courses to your shopping cart. The admin panel can be accessed by authorized users for managing tutorials, courses, and users.

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

MIT.

## Contact

If you have any questions or concerns, feel free to contact the project maintainer(s) at <edwin.nwofor@yahoo.com>.
