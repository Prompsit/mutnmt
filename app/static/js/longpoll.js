(function() {
    /*
        @param timeout Poll the server every timeout seconds
        @param ajax_opt jQuery AJAX options
        @param success_fn Function to call with the server response. If it returns False, long-polling is stopped
        @param immediate True to start polling immediately, False to wait timeout seconds
    */
    let longpoller = (timeout, ajax_opt, success_fn, immediate) => {
        let perform_request = () => {
            $.ajax(ajax_opt).done(function(response) {
                let success_fn_res = success_fn(response);
                if (success_fn_res !== false) setTimeout(perform_request, timeout);
            });
        }

        if (immediate) {
            perform_request();
        } else {
            setTimeout(perform_request, timeout);
        }
    }

    window.longpoll = longpoller;
})(window);