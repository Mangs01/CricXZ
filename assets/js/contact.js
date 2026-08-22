document.addEventListener("DOMContentLoaded", function () {
    const contactForm = document.getElementById("contactForm");
    const contactFormMessage = document.getElementById("contactFormMessage");

    if (!contactForm || !contactFormMessage) {
        return;
    }

    contactForm.addEventListener("submit", function (event) {
        event.preventDefault();
        contactFormMessage.hidden = false;
    });
});
