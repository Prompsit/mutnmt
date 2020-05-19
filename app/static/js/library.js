$(document).ready(function() {
    $('.corpora-table').each(function(i, el) {
        let public_mode = ($(el).attr("data-public") == "true");
        let corpora_table = $(el).DataTable({
            processing: true,
            serverSide: true,
            responsive: true,
            ajax: {
                url: "corpora_feed",
                method: "post",
                data: { public: public_mode }
            },
            drawCallback: function(settings) {
                let api = this.api()
                let rows = api.rows({ page: 'current' }).nodes();
                let row_data = api.rows({ page: 'current' }).data()
                let last_group = -1;
                rows.each(function(row, i) {
                    let data = row_data[i];
                    let corpus_data = data[8];
                    
                    if (corpus_data.corpus_id != last_group) {
                        let template = document.importNode(document.querySelector("#corpus-header-template").content, true);
                        $(template).find(".corpus_name").html(corpus_data.corpus_name);

                        if (corpus_data.corpus_description != "") {
                            $(template).find(".corpus_description").html(corpus_data.corpus_description);
                        } else {
                            $(template).find(".corpus-description-row").addClass("d-none");
                        }
                        
                        $(template).find(".corpus_lang_src").html(corpus_data.corpus_source);
                        $(template).find(".corpus_lang_trg").html(corpus_data.corpus_target);
                        $(template).find(".corpus_uploader").html(corpus_data.corpus_uploader);

                        if (corpus_data.corpus_owner) {
                            if (corpus_data.corpus_public) {
                                $(template).find(".folder-shared").removeClass("d-none");
                            } else {
                                $(template).find(".folder-owner").removeClass("d-none");
                            }
                        } else {
                            $(template).find(".folder-grabbed").removeClass("d-none");
                        }
                        
                        $(template).find(".export-btn").attr("href", corpus_data.corpus_export);
                        $(template).find(".corpus-preview").attr("href", corpus_data.corpus_preview);

                        if (public_mode) {
                            $(template).find(".grab-btn").attr("href", corpus_data.corpus_grab);
                            $(template).find(".grab-btn").removeClass("d-none");
                        } else {
                            if (corpus_data.corpus_owner) {
                                if (corpus_data.corpus_public) {
                                    $(template).find(".corpus-stop-share").attr("href", corpus_data.corpus_share);
                                    $(template).find(".corpus-stop-share").removeClass("d-none");
                                } else {
                                    $(template).find(".corpus-share").attr("href", corpus_data.corpus_share);
                                    $(template).find(".corpus-share").removeClass("d-none");
                                }

                                $(template).find(".corpus-delete").attr("href", corpus_data.corpus_delete);
                                $(template).find(".corpus-delete").removeClass("d-none");
                            } else {
                                $(template).find(".corpus-ungrab").attr("href", corpus_data.corpus_ungrab);
                                $(template).find(".corpus-ungrab").removeClass("d-none");
                            }
                        }


                        $(row).before(template);
                        last_group = corpus_data.corpus_id;
                    }
                })
            },
            columnDefs: [
                {
                    targets: [0, 1, 2, 3, 4, 5, 6, 7],
                    responsivePriority: 1
                },
                { 
                    targets: 0,
                    responsivePriority: 1,
                    className: "border-right-0 align-middle text-center",
                    render: function(data, type, row) {
                        let corpus_data = row[8];
                        let template = document.importNode(document.querySelector("#preview-button-template").content, true);
                        $(template).find(".file-item-preview").attr("href", corpus_data.file_preview);
                        let ghost = document.createElement('div');
                        $(ghost).append(template);
                        return ghost.innerHTML;
                    }
                },
                {
                    targets: 1,
                    responsivePriority: 1,
                    className: "overflow",
                    render: function(data, type, row) {
                        let corpus_data = row[8];
                        let template = document.importNode(document.querySelector("#corpus-entry-template").content, true);
                        $(template).find(".file-name").html(data);

                        let ghost = document.createElement('div');
                        $(ghost).append(template);
                        return ghost.innerHTML;
                    }
                },
                { 
                    targets: 7,
                    responsivePriority: 1,
                    className: "actions",
                    searchable: false,
                    sortable: false,
                    render: function(data, type, row) {
                        return ""
                    }
                }
            ]
        });
    });

    $(".engines-table").each(function(i, el) {
        let public_mode = ($(el).attr("data-public") == "true");
        $(el).DataTable({
            processing: true,
            serverSide: true,
            responsive: true,
            ajax: {
                url: "engines_feed",
                method: "post",
                data: { public: public_mode }
            },
            columnDefs: [
                { 
                    targets: 0,
                    responsivePriority: 1,
                    searchable: false,
                    sortable: false,
                    class: "text-center border-right-0",
                    render: function(data, type, row) {
                        let engine_data = row[7];
                        let template = document.importNode(document.querySelector("#engines-icon-template").content, true);

                        if (engine_data.engine_owner) {
                            if (engine_data.public) {
                                $(template).find(".folder-shared").removeClass("d-none");
                            } else {
                                $(template).find(".folder-owner").removeClass("d-none");
                            }
                        } else {
                            $(template).find(".folder-grabbed").removeClass("d-none");
                        }

                        let ghost = document.createElement('div');
                        $(ghost).append(template);

                        return ghost.innerHTML;
                    }
                },
                { 
                    targets: 6,
                    responsivePriority: 1,
                    className: "actions",
                    searchable: false,
                    sortable: false,
                    render: function(data, type, row) {
                        let engine_data = row[7];
                        let template = document.importNode(document.querySelector("#engines-options-template").content, true);

                        $(template).find(".export-btn").attr("href", engine_data.engine_export);

                        $(template).find(".detail-btn").attr("href", engine_data.engine_detail);
                        $(template).find(".detail-btn").removeClass("d-none");

                        if (public_mode) {
                            $(template).find(".grab-btn").attr("href", engine_data.engine_grab);
                            $(template).find(".grab-btn").removeClass("d-none");
                        } else {
                            if (engine_data.engine_owner) {
                                if (engine_data.engine_public) {
                                    $(template).find(".stop-sharing-btn").attr("href", engine_data.engine_share);
                                    $(template).find(".stop-sharing-btn").removeClass("d-none");
                                } else {
                                    $(template).find(".share-btn-btn").attr("href", engine_data.engine_share);
                                    $(template).find(".share-btn-btn").removeClass("d-none");
                                }

                                $(template).find(".summary-btn").attr("href", engine_data.engine_summary);
                                $(template).find(".summary-btn").removeClass("d-none");

                                $(template).find(".delete-btn").attr("href", engine_data.engine_delete);
                                $(template).find(".delete-btn").removeClass("d-none");
                            } else {
                                $(template).find(".remove-btn").attr("href", engine_data.engine_ungrab);
                                $(template).find(".remove-btn").removeClass("d-none");
                            }
                        }

                        let ghost = document.createElement('div');
                        ghost.appendChild(template);
                        return ghost.innerHTML;
                    }
                }
            ]
        });
    });

    $(".details-table").DataTable({
        dom: "t",
        paging: false,
        columnDefs: [{
            targets: 4,
            sortable: false
        }]
    });

    $(".nav-tabs a").on('shown.bs.tab', function() {
        $(".tab-pane.active .dataTable").each(function(i, el) {
            $(el).DataTable().ajax.reload();
        })
    })
});