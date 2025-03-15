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

//hard filling


let totalCapacity = 500;  
let currentCapacity = 0;  


function addGame(gameSize) {
   
    if (currentCapacity + gameSize <= totalCapacity) {
        currentCapacity += gameSize;

     
        let fillPercentage = (currentCapacity / totalCapacity) * 100;
        document.getElementById('hardDiskFill').style.width = fillPercentage + '%';

 
        document.getElementById('capacityText').innerText = `${currentCapacity} GB / ${totalCapacity} GB`;

      
        if (currentCapacity === totalCapacity) {
            document.getElementById('hardDiskFill').style.backgroundColor = 'black';
        }
    } else {
        alert('Not enough space on the hard disk!');
    }
}

// Example of adding games
addGame(10); // Add a game of 20 GB
addGame(30); // Add a game of 30 GB
addGame(20);
addGame(20); // Add a game of 50 GB

