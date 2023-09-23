$(document).ready(function () {
    // Attach a click event handler to each category link
    $(".nav-link").click(function () {
        // Get the category name from the clicked link's ID
        var categoryName = $(this).attr("id").replace("nav-", "").replace("-tab", "");

        // Hide all product containers initially
        $(".tab-pane").hide();

        // Show the product container for the selected category
        $("#nav-" + categoryName).show();
    });
});