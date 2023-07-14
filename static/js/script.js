// function generateAndUploadPdf() {
//     console.log("generateAndUploadPdf called");
//     var url = window.location.href;
//     window.location.href = '/generate_and_upload_pdf?url=' + encodeURIComponent(url);
// }
$(document).ready(function() {
    // print button functionality
    $('#printBtn').click(function() {
      window.print();
    });
  

    // form submission functionality
    $('#medicalDocument').on('input', function() {
      var formData = {};
      $('#medicalDocument span').each(function() {
        formData[$(this).attr('id')] = $(this).text();
      });
  
      // send AJAX request to Flask server
      $.ajax({
        type: 'POST',
        url: '/submit',
        data: JSON.stringify(formData),
        contentType: 'application/json',
        success: function(response) {
          console.log(response);
        },
        error: function(error) {
          console.log(error);
        }
      });
    });
  });