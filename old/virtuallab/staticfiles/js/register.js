const passwordInput = document.getElementById('password');
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