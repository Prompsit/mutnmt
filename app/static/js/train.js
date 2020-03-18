$(document).ready(function() {
    const interval = 1000;

    let setupTimer = (el) => {
        let timestamp = parseInt($(el).attr("data-started"));
        let begin = moment();
        let end = moment.unix(timestamp).add($(el).attr("data-minutes"), 'minutes');
        let duration = moment.duration(end.diff(begin))

        $(el).html(moment.utc(duration.asMilliseconds()).format("mm:ss"))
    }

    $(".time-left").each(function(i, el) {
        setupTimer(el)
        setInterval(() => {
            setupTimer(el)
        }, interval);
    });
});