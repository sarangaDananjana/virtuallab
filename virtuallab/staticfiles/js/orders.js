// Grab elements
const selectElement = selector => {
    const element = document.querySelector(selector)
    if (element) return element;
    throw new Error(`Somthing went,make sure that $(selector) exist or is typed correctly.`);

};

//Nav styles on scroll
const scrollHeader = () => {
    const headerElement = selectElement('#header');
    if (this.scrollY >= 15) {
        headerElement.classList.add('activated');

    } else {
        headerElement.classList.remove('activated');
    }
};
// Open menu & search pop-up
window.addEventListener('scroll', scrollHeader);

const menuToggleIcon = selectElement("#menu-toggle-icon");

const toggleMenu = () => {
    const mobileMenu = selectElement('#menu');
    mobileMenu.classList.toggle('activated');
    menuToggleIcon.classList.toggle('activated');
};
// Open/Close search form popup
menuToggleIcon.addEventListener('click', toggleMenu);


const navLinks = document.querySelectorAll('.list-link');
const sections = document.querySelectorAll('section'); 


function highlightNavOnScroll() {
    let scrollPosition = window.scrollY;

    sections.forEach((section) => {
        const sectionTop = section.offsetTop - 100;// Adjust this offset according to your header height
        const sectionHeight = section.offsetHeight;
        const sectionId = section.getAttribute('id');

        // Check if the scroll position is within this section
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            
            navLinks.forEach((link) => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${sectionId}`) {
                    link.classList.add('active');
                }
            });
        }
    });
}


function showOrders(tab) {
    // Hide both orders sections
    document.getElementById('pending').style.display = 'none';
    document.getElementById('completed').style.display = 'none';

    // Remove the active class from both tabs
    document.getElementById('pending-tab').classList.remove('active-tab');
    document.getElementById('completed-tab').classList.remove('active-tab');

    // Show the selected tab
    document.getElementById(tab).style.display = 'block';

    // Add the active class to the clicked tab
    if (tab === 'pending') {
        document.getElementById('pending-tab').classList.add('active-tab');
    } else {
        document.getElementById('completed-tab').classList.add('active-tab');
    }
}

function toggleDetails(element) {
    // Get the corresponding order details element
    const details = element.parentElement.querySelector('.order-details');

    // Toggle visibility
    if (details.style.display === 'none' || details.style.display === '') {
        details.style.display = 'block';  // Show the details
        element.querySelector('i').classList.remove('fa-chevron-down');
        element.querySelector('i').classList.add('fa-chevron-up');  // Change to up arrow
    } else {
        details.style.display = 'none';  // Hide the details
        element.querySelector('i').classList.remove('fa-chevron-up');
        element.querySelector('i').classList.add('fa-chevron-down');  // Change back to down arrow
    }
}

// Set the default tab to "pending" when the page loads
window.onload = function () {
    showOrders('pending');  // Show the pending orders by default
};




//profile
const profileCircle = document.getElementById('profileCircle');
const dropdownMenu = document.getElementById('dropdownMenu');

profileCircle.addEventListener('click', function() {
    dropdownMenu.classList.toggle('hidden');
});

// Optional: Close the dropdown if clicked outside
document.addEventListener('click', function(event) {
    if (!profileCircle.contains(event.target) && !dropdownMenu.contains(event.target)) {
        dropdownMenu.classList.add('hidden');
    }
});