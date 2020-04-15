$(document).ready(function() {

    // Translates the source text and displays
    // the translation in a textarea
    let translate = () => {

        // If the engine is ready, we capture each line of text and
        // we send it to the server
        if ($('.live-translate-form').attr('data-status') == 'ready') {
            // If there is no text, we do nothing
            if ($('.live-translate-source').val() == "") {
                $('.live-translate-target').html("");
                return;
            }

            let text = [];
            for (let line of $('.live-translate-source').val().split('\n')) {
                text.push(line)
            }

            $.ajax({
                url: `get`,
                method: "POST",
                data: { text: text }
            }).done(function(data) {
                // We fill target text depending on the result from the server
                $('.live-translate-target').html("");

                if (data.result == -1) {
                    $('.live-translate-form').attr('data-status', 'error')
                } else {
                    if (data.lines) {
                        for (let line of data.lines) {
                            let line_element = document.createTextNode(line + '\n');
                            $('.live-translate-target').append(line_element);
                        }
                    }
                }
            });
        } else if ($('.live-translate-form').attr('data-status') != 'launching') {
            // If the engine is not ready (and it is not launching), we launch it
            $('.live-translate-form').attr('data-status', 'launching');

            $.ajax({
                url: `attach_engine/${$('.engine-select option:selected').val()}`
            }).done(function(raw) {
                if (raw == "0") {
                    $('.live-translate-form').attr('data-status', 'ready');
                    translate()
                } else {
                    $('.live-translate-form').attr('data-status', 'error');
                }
            });
        }

        return false;
    }

    // When we change the selected engine, we automatically translate
    $('.engine-select').on('change', function() {
        $('.live-translate-form').attr('data-status', 'false');

        if ($('.live-translate-source').val() != "") {
            translate()
        }
    });

    // Translation is performed when the user types. We skip some
    // of the calls for performace sake. Anyway, when the user stops
    // typing, we translate the whole text (that's what the watcher is for)
    let watcher;
    let count = 0;

    $('.live-translate-source').on('keyup', function() {
        if (watcher) clearTimeout(watcher);
        watcher = setTimeout(() => {
            translate()
        }, 700);

        if (count > 5) {
            translate();
            count = 0;
        }

        count++;

        if ($(this).val() != "") {
            $(this).parent().addClass("filled");
        } else {
            $(this).parent().removeClass("filled");
        }
    });

    // Some functionality for links and textareas
    $('.engine-relaunch-btn').on('click', function(e) {
        e.preventDefault();
        translate();
    })

    $('.custom-textarea textarea').on('focus', function() {
        $(this).parent().addClass("focus");
        $(this).parent().find(".custom-textarea-placeholder").addClass("d-none");
    });

    $('.custom-textarea textarea').on('blur', function() {
        $(this).parent().removeClass("focus");
        $(this).parent().find(".custom-textarea-placeholder").removeClass("d-none");
    });
});

// We let the server know we quit this window, to close the translator
$(window).on('unload', function() {
    if (navigator.sendBeacon) {
        navigator.sendBeacon('leave');
    } else {
        $.ajax({ url: `leave`, async: false, type: "post" });
    }
});