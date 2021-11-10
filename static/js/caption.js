    const x = setInterval(load_updated_part,1000);
    let counter = 0;
    let stored_caption = null;
function load_updated_part() {
    let url = window.location.href;
    if (stored_caption !== null){
        url = url + "&seconds=" + String(counter)
    }
    url = url + "&seconds=" + String(counter)
    counter += 1;
    const result = fetch(url = url).then(function (response) {
        return response.json().then(function (renewed_json_text) {
            if (renewed_json_text.length === 0){
                return;
            }
            let text_for_updates = "";
            if (stored_caption === null){
                stored_caption = renewed_json_text;
            } else {
                console.log(stored_caption[stored_caption.length-1]['start'],renewed_json_text[renewed_json_text.length-1]['start']);
                if (stored_caption[stored_caption.length-1]['start'] === renewed_json_text[renewed_json_text.length-1]['start']){
                    stored_caption.splice(-1,1)
                    stored_caption.push(renewed_json_text[renewed_json_text.length-1])
                } else {
                    stored_caption.push(renewed_json_text[renewed_json_text.length-1])
                }
            }
            for (let item of stored_caption.slice().reverse()) {
              text_for_updates += item["actor"]+"::"+item["session"]+"::"+item["start"]+"::"+item["text"]
              text_for_updates += "<br>";
            }
            document.getElementById("textpart").innerHTML = text_for_updates;
        });
    });
}
