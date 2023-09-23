const password = document.getElementById("fakePassword");
const toggler = document.getElementById("passwordToggler");

const showHidePassword = () => {
    if (password.type === "password") {
        password.setAttribute("type", "text");
        toggler.classList.add("bi-eye");
        toggler.classList.remove("bi-eye-slash");
    } else {
        toggler.classList.remove("bi-eye");
        toggler.classList.add("bi-eye-slash");
        password.setAttribute("type", "password");
    }
};

toggler.addEventListener("click", showHidePassword);
