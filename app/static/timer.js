// Start game timer functionality
let timeRemaining;
function startTimer(duration, element, isIndex, user) {
    timeRemaining = duration;
    element.html(element.html().substring(0, element.html().length-1) + " " + parseInt(timeRemaining,10));
    let id = setInterval(function () {
        timeRemaining--;
        stopTimer(id, timeRemaining, element, isIndex, user);
    }, 1000);
}

function stopTimer(id, timeRemaining, element, isIndex, userCode) {
    if (timeRemaining < 0) {
        clearInterval(id);
        startGame = true;
        if (isIndex)
            window.location.replace(playUrl + userCode);
        else
            element.html("First to 5 points wins!");
    }
    else
        element.html(element.html().substring(0, element.html().length-1) + " " + parseInt(timeRemaining,10));
}