function set_toggle_contest_groups() {
    $('#standings_list .contest .toggle').click(function() {
        var selector = $(this).attr('data-group')
        $(selector).slideToggle(200, 'linear').css('display', 'table-row');
        $('[data-group="' + selector +  '"] i').toggleClass('fa-caret-up').toggleClass('fa-caret-down')
        event.preventDefault()
    }).removeClass('toggle')
}

$(set_toggle_contest_groups)

$(() => {
    $('#reparse').click(function() {
        bootbox.confirm({
            size: 'small',
            message: 'Are you sure you want to reparse all standings?',
            callback: function (result) {
                if (!result) {
                    return
                }
                $.ajax({
                    type: 'POST',
                    data: {'action': 'reparse'},
                    success: function(data) { location.reload() },
                    error: log_ajax_error_callback,
                })
            }
        })
    })
})
