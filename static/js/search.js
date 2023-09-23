$(document).ready(function () {
    $("#search-input").on("keyup", function () {
        var searchText = $(this).val().toLowerCase();

        $('table tbody tr').each(function () {
            var searchContent = $(this).data('search').toLowerCase();

            if (searchContent.includes(searchText)) {
                $(this).show();
            } else {
                $(this).hide();
            }
        })
    })
})