// Start game timer functionality
function startTimer(duration, element, isIndex, user) {
    let timeRemaining = duration
    element.html(element.html().substring(0, element.html().length-1) + " " + parseInt(timeRemaining,10))
    let id = setInterval(function () {
        timeRemaining--
        element.html(element.html().substring(0, element.html().length-1) + " " + parseInt(timeRemaining,10))
        stopTimer(id, timeRemaining, element, isIndex, user)
    }, 1000);
}

function stopTimer(id, timeRemaining, element, isIndex, user) {
    if (timeRemaining < 0) {
        clearInterval(id);
        element.hide();
        startGame = true;
        if (isIndex)
            window.location.replace("http://127.0.0.1:5000/play/" + user);
    }
}