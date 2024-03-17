document.getElementById('grading-form').addEventListener('submit', function(event) {
    event.preventDefault();

    var pdfUpload = document.getElementById('pdf-upload').files[0];
    var rubric = document.getElementById('rubric').value;
    var filename = pdfUpload.name; // Get the uploaded file name

    var formData = new FormData();
    formData.append('pdf', pdfUpload);
    formData.append('rubric', rubric);

    fetch('/grade', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log(data); // Add this to log the response data
        document.getElementById('response').innerText = data.feedback;
    })
    .catch((error) => {
        console.error('Error:', error);
    }); 
});