let FileDnD = (selector, on_file_dragged) => {
    let on_drop = function(dropped, el) {
        $(el).find(".file-dnd-name").html(dropped.name);
        $(el).addClass("dragged");
        on_file_dragged(dropped);
    }

    $(selector).on('drag dragstart dragend dragover dragenter dragleave drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
    }).on('dragover dragenter', function() {
        $(this).addClass("dragging");
    }).on('dragleave dragend drop', function() {
        $(this).removeClass("dragging");
    }).on('drop', function(e) {
        on_drop(e.originalEvent.dataTransfer.files[0], this);
    });

    $(selector).find(".file-dnd-input").on("change", function() {
        on_drop(this.files[0], selector)
    });
}
