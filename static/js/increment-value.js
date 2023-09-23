$(".input-group").on("click", ".button-plus", function (event) {
    event.preventDefault();
    var target = $(event.target);
    var field = target.data("field");
    var container = target.closest("div");
    var input = container.find("input[name=" + field + "]");
    var value = parseInt(input.val(), 10);

    if (!isNaN(value) && value < 10) {
        input.val(value + 1);
    } else {
        input.val(10); // Set the value to the upper limit (10) if it's not a number or already at the limit.
    }
});

$(".input-group").on("click", ".button-minus", function (event) {
    event.preventDefault();
    var target = $(event.target);
    var field = target.data("field");
    var container = target.closest("div");
    var input = container.find("input[name=" + field + "]");
    var value = parseInt(input.val(), 10);

    if (!isNaN(value) && value > 0) {
        input.val(value - 1);
    } else {
        input.val(0); // Set the value to 0 if it's not a number or already at 0.
    }
});