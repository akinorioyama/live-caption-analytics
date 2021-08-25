function doPost(e) {

  var ss = SpreadsheetApp.getActive()
  var sheet = ss.getActiveSheet();

  let params = JSON.parse(e.postData.contents);

  let last_row = sheet.getLastRow();
  if (last_row === 0){
    last_row = 1;
  }
  let values  = sheet.getRange(last_row,2,1,2).getValues();
  let start = values[0][0];
  let end = values[0][1];
  if ( start === params.transcript[0][0] & end === params.transcript[0][1]){
  } else if (start === params.transcript[0][0] & end !== params.transcript[0][1]){
    sheet.getRange(last_row,3,1,1).setValue(params.transcript[0][1]);
    sheet.getRange(last_row,5,1,1).setValue(params.transcript[0][3]);
  } else {
    let obj_row = params.transcript[0];
    obj_row.unshift(params.transcriptId);
    sheet.appendRow(obj_row);
  }

   var response = {
    'response': 'success'
  };
  return ContentService.createTextOutput(JSON.stringify(response)).setMimeType(ContentService.MimeType.JSON);
}

function doGet(e){
  return ContentService.createTextOutput("");
}