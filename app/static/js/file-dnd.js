let FileDnD = (selector, on_file_dragged, body_drag = false) => {
    let on_drop = function(dropped, el) {
        $(el).find(".file-dnd-name").html(dropped.name);
        $(el).addClass("dragged");
        on_file_dragged(dropped);
    }

    if (body_drag) {
        $("body").on('drag dragstart dragend dragover dragenter dragleave drop', function() {
            $(selector).addClass("dragging");
        }).on('dragleave dragend drop', function() {
            $(selector).removeClass("dragging");
        });
    }

    $(selector).on('drag dragstart dragend dragover dragenter dragleave drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
    }).on('dragover dragenter', function() {
        $(this).addClass("dragging");
        $(this).addClass("dropping");
    }).on('dragleave dragend drop', function() {
        $(this).removeClass("dragging");
        $(this).removeClass("dropping");
    }).on('drop', function(e) {
        on_drop(e.originalEvent.dataTransfer.files[0], this);
    });

    $(selector).find(".file-dnd-input").on("change", function() {
        on_drop(this.files[0], selector)
    });
}
