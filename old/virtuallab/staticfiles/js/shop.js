document.addEventListener("DOMContentLoaded", () => {
    const buttons = document.querySelectorAll(".add-to-cart-btn");

    buttons.forEach(button => {
        button.addEventListener("click", (e) => {
            e.preventDefault();
            button.classList.toggle("clicked");
            if (button.classList.contains("clicked")) {
                button.textContent = "✔"; // Change to tick mark
            } else {
                button.textContent = "+"; // Revert back to "+"
            }
        });
    });
});
