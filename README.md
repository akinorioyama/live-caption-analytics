# live-caption-analytics
This chrome extension sends captions to servers to perform analytics and return feedback to the sender. Thanks to the author of [google-meet-transcripts](https://github.com/dzaman/google-meet-transcripts), the extension reads live caption in Google Meet.

The <b>chrome extension</b> will post the data to two of your servers to analyze or record live transcript. The one endpoint is to perform caption <b>analysis</b> and the other is to send the latest lines of caption to <b>record</b> in a storage, in the sample, a Google spreadsheet. Those two endpoints are independent from each other and can be called separately. This [YouTube video](https://www.youtube.com/watch?v=g1aYP5yyyJQ) will show the screen interaction in the browser.

**Building blocks**
---
`live-caption-analytics` has three building blocks listed below. 

***1) chrome extension*** part captures live caption and send (request) the portion to servers configured in option settings for the extension, and then receive (response) and render the response from the server. The extension is publicly available from [here](https://chrome.google.com/webstore/detail/pppkdkcchlonlocoiejjinmkdncfblji).

***2) analysis*** receives the caption data from the extension and will perform due calculations to return the response to the sender. The extension users can configure three options and can interact with the UI to control the POST requests to the endpoints, which are `/`, `/log`, `/show` and `/notification`.

***3) record*** sends the current caption line to a POST endpoint. The endpoint can be a Google spreadsheet as in the sample `receive_data.gs` in the folder `peripheral_functions/Google spreadsheet`. The POST enabled spreadsheet will update the received data to the dedicated sheet.

Each section is stored in the following paths.
```
src             <-- 1) chrome extension
main.py         <---2) analysis - sample implementation
receive_data.gs <-- 3) record - snippet to publish and will listen to POST calls
```
**Installation**
---
***1) chrome extension*** can be added via <i>"Add to Chrome"</i> from [here](https://chrome.google.com/webstore/detail/pppkdkcchlonlocoiejjinmkdncfblji) or via <i>Load unpackaged extension</i> from `chrome://extensions` by loading it from the folder `src`.

***2) analysis*** will start to listen simply by executing the main.py. Supply host and port in the argument. Configure the destination in the extention option `Server URL to record captions`. Running the script will create a sqllite database under the filename of `test.db`.

***3) record*** will receive caption once a Google spreadsheet has the sample `receive_data.gs` in a file and doPost is set up as a site in `deploy`. Configure the destination in the extention option `Server URL to record for Google Spreadsheet`.

**Documentation**
---
User documentation for the extension will be updated in `doc` folder.
