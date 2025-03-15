const passwordInput = document.getElementById('password1');
const requirements = {
    length: document.getElementById('requirement-length'),
    letter: document.getElementById('requirement-letter'),
    number: document.getElementById('requirement-number')
};

passwordInput.addEventListener('input', () => {
    const password = passwordInput.value;

    // Validate length
    if (password.length >= 8) {
        requirements.length.innerHTML = '<i class="ri-checkbox-circle-line text-green-500 mr-2"></i> At least 8 characters';
    } else {
        requirements.length.innerHTML = '<i class="ri-checkbox-blank-circle-line mr-2"></i> At least 8 characters';
    }

    // Validate letter
    if (/[a-zA-Z]/.test(password)) {
        requirements.letter.innerHTML = '<i class="ri-checkbox-circle-line text-green-500 mr-2"></i> At least one letter';
    } else {
        requirements.letter.innerHTML = '<i class="ri-checkbox-blank-circle-line mr-2"></i> At least one letter';
    }

    // Validate number
    if (/[0-9]/.test(password)) {
        requirements.number.innerHTML = '<i class="ri-checkbox-circle-line text-green-500 mr-2"></i> At least one number';
    } else {
        requirements.number.innerHTML = '<i class="ri-checkbox-blank-circle-line mr-2"></i> At least one number';
    }
});




// Get references to the password inputs and reveal icons
var passwordField1 = document.getElementById('password1');
var revealIcon1 = document.getElementById('reveal-icon1');

var passwordField2 = document.getElementById('password2');
var revealIcon2 = document.getElementById('reveal-icon2');

// Show the reveal icon when the user starts typing in either password field
passwordField1.addEventListener('input', function() {
    if (passwordField1.value.length > 0) {
        revealIcon1.style.display = 'block';  // Show the reveal icon when there's input
    } else {
        revealIcon1.style.display = 'none';   // Hide the reveal icon when the input is empty
    }
});

passwordField2.addEventListener('input', function() {
    if (passwordField2.value.length > 0) {
        revealIcon2.style.display = 'block';  // Show the reveal icon when there's input
    } else {
        revealIcon2.style.display = 'none';   // Hide the reveal icon when the input is empty
    }
});

// Toggle password visibility when the reveal icon is clicked for the first password field
revealIcon1.addEventListener('click', function() {
    if (passwordField1.type === 'password') {
        passwordField1.type = 'text';       // Show the password
        revealIcon1.classList.remove('ri-eye-line');
        revealIcon1.classList.add('ri-eye-off-line');  // Change icon to "eye-off"
    } else {
        passwordField1.type = 'password';   // Hide the password
        revealIcon1.classList.remove('ri-eye-off-line');
        revealIcon1.classList.add('ri-eye-line');  // Change icon back to "eye"
    }
});

// Toggle password visibility when the reveal icon is clicked for the second password field
revealIcon2.addEventListener('click', function() {
    if (passwordField2.type === 'password') {
        passwordField2.type = 'text';       // Show the password
        revealIcon2.classList.remove('ri-eye-line');
        revealIcon2.classList.add('ri-eye-off-line');  // Change icon to "eye-off"
    } else {
        passwordField2.type = 'password';   // Hide the password
        revealIcon2.classList.remove('ri-eye-off-line');
        revealIcon2.classList.add('ri-eye-line');  // Change icon back to "eye"
    }
});




