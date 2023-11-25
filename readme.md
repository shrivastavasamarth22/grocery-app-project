# FreshCart

FreshCart is an online grocery store web application built using Python and Flask. It allows users to browse and purchase groceries, manage their cart, and place orders. The application also includes a dashboard for managers to monitor and manage categories, products, orders, customers, and promotional codes.

## Getting Started

To run FreshCart locally on your machine, follow these steps:

1. Create a virtual environment to isolate project dependencies:
   ```
   python -m venv venv
   ```
   
2. Activate the virtual environment:
   ```
   venv/Scripts/activate
   ```

3. Install the project dependencies using pip:
   ```
   pip install -r requirements.txt
   ```
   

4. Start the Flask development server:
   ```
   flask run
   ```

5. Access the FreshCart web application by opening a web browser and navigating to `http://localhost:5000`.

## Usage

- Users can sign up, sign in, and browse products.
- Users can add products to their cart, view their cart, and proceed to checkout.
- Managers can sign in to the dashboard to manage categories, products, orders, customers, and promotional codes.

## Project Structure

The project is organized into various directories, including:

- `app`: Contains the Flask application code.
- `templates`: Contains HTML templates for rendering pages.
- `static`: Contains static assets like CSS, JavaScript, and images.
- `venv`: The Python virtual environment.

## Technologies Used

- Flask: A Python web framework.
- SQLAlchemy: An Object-Relational Mapping (ORM) library for Python.
- SQLite: A lightweight relational database management system.
- Jinja2: A templating engine for rendering dynamic content in HTML templates.

## Todos

- [ ] Initialise cart as soon as user signs up
- [ ] Implement stock quantity deduction logic on checkout
- [ ] Add order details page

