$(document).ready(function() {
    let fill_showcase = (sc) => {
        $.ajax({
            method: "post",
            url: "../stream",
            data: {
                file_id: $(sc).data("file-id"),
                start: $(sc).data("start"),
                offset: $(sc).data("offset")
            },
            success: function(data) {
                $(sc).data("start", parseInt($(sc).data("start") + $(sc).data("offset")));
                for (let line of data.lines) {
                    let template = document.importNode(document.querySelector("#parafile-line-template").content, true);
                    $(template).find(".parafile-line-content").html(line);
                    $(sc).append(template)
                }
            }
        })
    }

    $(".parafile-showcase").scrollTop(0);

    let control;
    $(".parafile").each(function(i, pa) {
        $(pa).find(".parafile-showcase").each(function(j, sc) {
            fill_showcase(sc);

            let scrollend, offset;
            $(sc).on('scroll', function() {
                // Propagate scroll
                if (scrollend) clearTimeout(scrollend)
                scrollend = setTimeout(() => { 
                    if (control == $(sc).data("file-id")) {
                        // Free control
                        control = undefined;
                        offset = undefined;
                    }
                }, 50);

                if (!control) {
                    control = $(sc).data("file-id");
                }

                if (control == $(sc).data("file-id")) {
                    // Highlight line
                    if ($('.parafile-showcase').not(sc).length > 0) {
                        let line = { i: -1 };
                        $(sc).find('.parafile-line').each(function(k, l) {
                            if (line.i == -1 && (($(l).offset().top + $(l).height() - 25) - $(sc).offset().top) >= 0) {
                                $('.parafile-line').removeClass("active");
                                $(l).addClass("active");
                                line = { i: k, el: l };
                            }
                        });
                        
                        let other_line = $('.parafile-showcase').not(sc).find('.parafile-line').eq(line.i);
                        other_line.addClass("active");
                    }

                    $(".parafile-showcase").not(sc).scrollTop($(sc).scrollTop());
                }
            });
        });
    });
});