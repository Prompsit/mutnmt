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

    let control, scrollend;
    $(".parafile").each(function(i, pa) {
        $(pa).find(".parafile-showcase").each(function(j, sc) {
            fill_showcase(sc);

            $(sc).on('scroll', function() {
                let file_id = $(sc).attr("data-file-id");
                if (!control) control = file_id

                if (control == file_id) {
                    // Schedule release of control
                    if (scrollend) clearTimeout(scrollend)
                    scrollend = setTimeout(() => {
                        control = undefined;
                    }, 50);

                    let active_line;
                    let scroll_top = $(sc).offset().top;

                    let line_index = 0;
                    for (let line_el of sc.querySelectorAll(".parafile-line")) {
                        let line_top = $(line_el).offset().top;
                        if (line_top >= scroll_top) {
                            $(".parafile-line").removeClass("active");
                            $(line_el).addClass("active");
                            active_line = { i: line_index, el: line_el };
                            break;
                        }

                        line_index++;
                    }

                    // Highlight line and scroll the other parafile
                    let other_sc = $(".parafile-showcase").not(sc);
                    let other_line = $(".parafile-showcase").not(sc).find(".parafile-line").eq(active_line.i)
                    other_line.addClass("active");

                    let prediction = $(other_line).offset().top - ($(sc).scrollTop() - $(other_sc).scrollTop());
                    let predicted_offset = prediction - $(active_line.el).offset().top;
                    other_sc.scrollTop($(sc).scrollTop() + predicted_offset);
                }
            });
        });
    });
});