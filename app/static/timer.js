// Start game timer functionality
let timeRemaining;
let nextPage;
let message;
let finalMessage;
function startTimer(duration, element, url, text, dialogText) {
    nextPage = url;
    timeRemaining = duration;
    message = text;
    finalMessage = dialogText;
    element.html(text + parseInt(timeRemaining,10));
    const dialog = $('.dialog');
    let id = setInterval(function () {
        timeRemaining--;
        if (timeRemaining + 5 < duration && dialog.length)
            dialog.dialog("close");
        stopTimer(id, timeRemaining, element, nextPage, message, finalMessage);
    }, 1000);
}

function stopTimer(id, timeRemaining, element, url, text, dialogText) {
    if (timeRemaining < 0) {
        clearInterval(id);
        startGame = true;
        if (url != null) {
            user = '';
            window.location.replace(url);
        }
        else if (dialogText != null)
            element.html(dialogText);
    }
    else
        element.html(text + parseInt(timeRemaining,10));
}

function setUrl(url) {
    nextPage = url;
}

function setText(text) {
    message = text;
}

function setDialogText(dialogText) {
    finalMessage = dialogText
}