const apiKey = PropertiesService.getScriptProperties().getProperty('genAIKey');
function testRun() {
    generateFormQuestions(5, 'easy', 'AI', 'English', 'ai-choice', true);  
}
function generateFormQuestions(amount, difficulty, topic, language, questionType, isQuiz) {
    const payload = {
      contents: [
        {
          parts: [
            { text: `Generate ${amount} Google Form questions with difficulty level ${difficulty} about "${topic}" in "${language}". 
Use the question type "${questionType}". If the type is "ai-choice", pick and choose from based on the question:
Short Answer (SA), Long Answer (LA), Multiple Choice (MC), Checkbox - Has Multiple Answers (CB), Dropdown (DD), 
Linear Scale (LS), Rating (RT), Multiple Choice Grid (MCG), Checkbox Grid (CG), Date (DT), Time (TT).

Your output must be a valid JSON object in this format:
{
  "questions": ["Question 1", "Question 2", ...],
  "types": ["MC", "SA", ...],
  "answers": ["Answer 1", "Answer 2", ...]
}

Rules:
- If isQuiz = true, include an "answers" key in the output.
  - For Multiple Choice, Checkbox, Dropdown, etc: format the answer for the question in the "answers" array as {"Actual Answer": [choice1, choice2, choice3, choice4]}.
  - For grid types (MCG, CG), format the answer for the question in the "answers" array as:
    {
      "row1": ["Answer A", "Answer B"],
      "row2": ["Answer C", "Answer D"]
    }
  - For short/long answer or others without clear choices, you can use simple strings or null.
- If isQuiz = false, do not include the "answers" key at all — just return "questions" and "types", else explicitly include "answers". There should be no null values in the "answers" array.

Only return valid JSON. No comments, no extra text, no markdown.` },
          ],
        },
      ],
    };
  
    const url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent';
    const options = {
      method: 'POST',
      contentType: 'application/json',
      headers: {
        'x-goog-api-key': apiKey,
      },
      payload: JSON.stringify(payload)
    };
  
    const response = UrlFetchApp.fetch(url, options);
    const data = JSON.parse(response);
    const content = data['candidates'][0]['content']['parts'][0]['text'];
    console.log(content);
}
function createForm() {
    var form = FormApp.create('New Form', false);
    var item = form.addCheckboxItem();
    item.setTitle('What condiments would you like on your hot dog?');
    item.setChoices([
        item.createChoice('Ketchup'),
        item.createChoice('Mustard'),
        item.createChoice('Relish')
    ]);
    form.addMultipleChoiceItem()
        .setTitle('Do you prefer cats or dogs?')
        .setChoiceValues(['Cats', 'Dogs'])
        .showOtherOption(true);
    form.addPageBreakItem()
        .setTitle('Getting to know you');
    form.addDateItem()
        .setTitle('When were you born?');
    form.addGridItem()
        .setTitle('Rate your interests')
        .setRows(['Cars', 'Computers', 'Celebrities'])
        .setColumns(['Boring', 'So-so', 'Interesting']);

    form.setPublished(true);

    Logger.log('Published URL: ' + form.getPublishedUrl());
    Logger.log('Editor URL: ' + form.getEditUrl());
}
