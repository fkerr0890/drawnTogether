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

function stopTimer(id, timeRemaining, element, isIndex, userCode) {
    if (timeRemaining < 0) {
        clearInterval(id);
        startGame = true;
        if (isIndex) {
            element.hide();
            window.location.replace(playUrl + userCode);
        }
        else
            element.html("First to 5 points wins!")
    }
}