document.getElementById("uploadForm").addEventListener("submit", function(event) {
    event.preventDefault(); 

    let formData = new FormData();
    let imageInput = document.getElementById("imageInput").files[0];

    if (!imageInput) {
        alert("Please select an image.");
        return;
    }

    formData.append("image", imageInput);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.result_image) {
            let resultImg = document.getElementById("resultImage");
            resultImg.src = data.result_image;
            resultImg.style.display = "block"; // Ensure it's visible
        } else {
            console.error("Error: No image returned", data);
        }
    })
    .catch(error => console.error("Error:", error));
});
