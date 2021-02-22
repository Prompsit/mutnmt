$(document).ready(function() {
    let file_as_tmx = false;

    $(".file-dnd-label").on('mouseenter', function() {
        if (!$(this).closest(".custom-textarea").hasClass("filled")) {
            $('.source-placeholder').addClass("d-none");
            $('.custom-textarea-file-upload').css({ display: 'block' });
            $('.custom-textarea-file-upload').animate({ opacity: 1 }, 500);
        }

        $('.btn-as-tmx').addClass("d-none")
    });

    $(".file-dnd-label").on('mouseleave', function() {
        if (!$(this).closest(".custom-textarea").hasClass("filled")) {
            $('.custom-textarea-file-upload').animate({ opacity: 0 }, 250, function() {
                $('.custom-textarea-file-upload').css({ display: 'none' });
                if ($(".live-translate-source").val() == "") {
                    $('.source-placeholder').removeClass("d-none");
                }
            });
        }
        
        $('.btn-as-tmx').removeClass("d-none")
    });

    $(".translate-file-tmx-btn").on('click', function() {
        file_as_tmx = true;
    })

    $(".chain-btn").on('click', function() {
        $("#chain").val("true");
        $(".chain-row").removeClass("d-none");
        $(this).addClass("d-none");
    });

    $(".chain-remove-btn").on('click', function() {
        $("#chain").val("false");
        $(".chain-row").addClass("d-none");
        $(".chain-btn").removeClass("d-none");
    });

    $(".btn-as-tmx").on("click", function(e) {
        e.preventDefault();

        let text = [];
        for (let line of $('.live-translate-source').val().split('\n')) {
            text.push(line)
        }

        $.ajax({
            url: 'as_tmx',
            method: 'POST',
            data: { 
                engine_id: $('.engine-select option:selected').val(),
                text: text,
                chain_engine_id: ($("#chain").val() == "true") ? $('.engine-select-chain option:selected').val() : "false"
            }
        }).done(function(task_data) {
            longpoll(2000, {
                url: 'get_tmx',
                method: 'POST',
                data: { task_id: task_data.task_id }
            }, (data) => {
                if (data.result == 200) {
                    window.location.href = data.url;
                    return false;
                }
            });
        })

        return false;
    })

    // Translates the source text and displays
    // the translation in a textarea
    let translate = () => {
        let show_translation = (data) => {
            if (data.result == -2) {
                $('.live-translate-form').attr('data-status', 'error')
            } else if (data.result == 200) {
                if (data.lines) {
                    for (let line of data.lines) {
                        line_proc = line.replaceAll('&lt;', '<').replaceAll('&gt;', '>');
                        let line_element = document.createTextNode(line_proc + '\n');
                        $('.live-translate-target').append(line_element);
                    }
                }

                $('.live-translate-form').attr('data-status', 'none');

                return false;
            }
        }

        let translate_text = (engine_id, text, callback) => {
            $.ajax({
                url: 'text',
                method: "POST",
                data: {
                    engine_id: engine_id,
                    text: text
                }
            }).done(function(task_data) {
                // We fill target text depending on the result from the server
                $('.live-translate-target').html("");

                longpoll(2000, {
                    url: 'get',
                    method: 'POST',
                    data: { task_id: task_data.task_id }
                }, (data) => {
                    return callback(data);
                });
            });
        }

        // We capture each line of text and we send it to the server
        // If there is no text, we do nothing
        if ($('.live-translate-source').val() == "") {
            $('.live-translate-target').html("");
            return;
        }

        let text = [];
        for (let line of $('.live-translate-source').val().split('\n')) {
            text.push(line)
        }

        if ($('.live-translate-form').attr('data-status') != 'launching') {
            $('.live-translate-target').html("");
            $('.live-translate-form').attr('data-status', 'launching');

            translate_text($('.engine-select option:selected').val(), text, (data) => {
                if (data.result == 200) {
                    if ($("#chain").val() == "true") {
                        translate_text($('.engine-select-chain option:selected').val(), data.lines, (data) => {
                            return show_translation(data);
                        });

                        return false;
                    } else {
                        return show_translation(data)
                    }
                }
            });
        }

        return false;
    }

    // When we change the selected engine, we automatically translate
    $('.engine-select').on('change', function() {
        $('.live-translate-form').attr('data-status', 'false');
        $('.live-translate-target').html("");

        if ($('.live-translate-source').val() != "") {
            translate()
        }
    });

    $('.live-translate-source').on('keyup', function() {
        if ($(this).val() != "") {
            $('.custom-textarea').addClass("filled");
        } else {
            $('.custom-textarea').removeClass("filled");
        }

        // Trick to make it shrink
        $(".live-translate-source, .live-translate-target").css({
            height: 'auto'
        });

        $(".live-translate-source, .live-translate-target").css({
            height: `${$(this)[0].scrollHeight}px`
        })
    });

    $('.translate-btn').on('click', function(e) {
        e.preventDefault();
        translate();
    })

    // Some functionality for links and textareas
    $('.engine-relaunch-btn').on('click', function(e) {
        e.preventDefault();
        translate();
    })

    $('.custom-textarea textarea').on('focus', function() {
        $(this).closest(".custom-textarea").addClass("focus");
        $(this).closest(".custom-textarea").find(".custom-textarea-placeholder").addClass("d-none");
    });

    $('.custom-textarea textarea').on('blur', function() {
        $(this).closest(".custom-textarea").removeClass("focus");
        $(this).closest(".custom-textarea").find(".custom-textarea-placeholder").removeClass("d-none");
    });

    // File translation
    let translate_file = (file) => {
        $('.live-translate-form').attr('data-status', 'file-translating');
        $('.live-translate-source').val('');
        $('.live-translate-source').prop('disabled', true);
        $('.custom-textarea').removeClass("filled");

        let data = new FormData();
        data.append("user_file", file);
        data.append("engine_id", $(".engine-select option:selected").val());
        data.append("as_tmx", file_as_tmx);
        data.append("tmx_mode", $(".tmx-mode-select .form-check-input:checked").val())

        $.ajax({
            url: '/translate/file',
            method: 'POST',
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            success: function(task_data) {
                file_as_tmx = false;
                $('.btn-as-tmx').removeClass("d-none");
                $('.live-translate-source').prop('disabled', false);

                longpoll(2000, {
                    url: 'get_file',
                    method: 'POST',
                    data: { task_id: task_data.task_id }
                }, (data) => {
                    if (data.result == 200) {
                        $('.live-translate-form').attr('data-status', 'ready');
                        $(".file-label-name").html("");
                        $(".file-label-text").css({ display: 'inline' });
                        window.location.href = data.url;
                        return false;
                    }
                });
            }
        });
    }

    FileDnD(".file-dnd", function(file) {
        $(".live-translate-target").html("");
        $(".file-label-text").css({ display: 'none' })
        $(".file-label-name").html(file.name);

        let re = /(?:\.([^.]+))?$/;
        let extension = re.exec(file.name)[1];
        if (extension == "tmx") {
            $('.live-translate-form').attr('data-status', 'tmx-dialog');
            $('.btn-confirm-tmx').on('click', function() {
                translate_file(file);
            })
        } else {
            $('.live-translate-form').attr('data-status', 'ready');
            translate_file(file);
        }
    }, true);
    
    $(".live-translate-form").on('submit', function() {
        if ($(".live-translate-source").val() == "") {
            return false;
        }
    })
});

// We let the server know we quit this window, to close the translator
$(window).on('unload', function() {
    if (navigator.sendBeacon) {
        navigator.sendBeacon('leave');
    } else {
        $.ajax({ url: `leave`, async: false, type: "post" });
    }
});