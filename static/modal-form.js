$("body").on("click", "#sales-modal-trigger", function(){
    $("#sales-modal").addClass("is-active");
  })

  $("body").on("click", ".modal-background", function(){
    $("#sales-modal").removeClass("is-active");
  })
  $("body").on("click", ".modal-close", function(){
    $("#sales-modal").removeClass("is-active");
  })

  $("body").on("click", "#gamesalesstats", function(e){
    e.preventDefault();

    var platform = $("#game-platform").val();
    var link = $("#game-link").val();
    var steamid = $("#game-steamid").val();
    var salesd1 = $("#game-salesd1").val();
    var salesw1 = $("#game-salesw1").val();
    var salesm1 = $("#game-salesm1").val();
    var salesy1 = $("#game-salesy1").val();
    var contact = $("#game-contact").val();

    axios({
      method: "post",
      url: "/sales",
      data: {
        platform: platform,
        link: link,
        steamid: steamid,
        salesd1: salesd1,
        salesw1: salesw1,
        salesm1: salesm1,
        salesy1: salesy1,
        contact: contact
      }
    })
    .then(function(){
      $("#sales-modal").removeClass("is-active");
      alert("Thank you!");
    })
    .catch(function(err){
      console.log(err);
      alert("There was an error, please try again later.")
    })

  });