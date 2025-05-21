# PerfumeSwap

This is a Django-based web application developed as a final thesis project.

## Project Overview

**PerfumeSwap** is an online platform for selling and swapping perfumes. The system allows users to:

- Browse perfumes by name, brand, or category (Men, Women, Unisex)
- View detailed product information with image, description, price, and stock
- Add products to a wishlist with a visible heart icon and wishlist counter
- Add items to a shopping cart with quantity selector and dynamic subtotal/total calculation
- Finalize orders by filling in delivery details
- View order history and track status (Confirmed, Shipped, Completed)
- Sellers can view incoming orders for their products and update order statuses
- Write and read reviews with average rating and total number of reviews shown per product
- Offer perfumes for trade with the ability to include optional extra payment
- Each user in a trade provides their own delivery info; addresses are revealed only after both submit their data
- View and manage trade offers through the “My Trades” section (Sent Offers, Received Offers, Trade History)
- Filter trade history by status (Completed, Rejected)
- Receive visual notifications (red badge counters) for new orders and received trade offers
- Reset forgotten passwords via email using Gmail SMTP and custom-styled templates

The goal of this project is to simulate a real-world e-commerce platform with trading functionality, tailored specifically to the perfume market.

## Technologies Used

- Python & Django
- HTML, CSS, Bootstrap
- JavaScript (for interactivity and AJAX)
- MySQL (production database)

## Author

This project was developed as part of a Bachelor's thesis in Computer and Software Engineering.
