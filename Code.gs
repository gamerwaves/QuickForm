const apiKey = PropertiesService.getScriptProperties().getProperty('genAIKey');

function testRun() {
    const raw = generateFormQuestions(11, 'medium', 'Elon Musk', 'English', 'all types 1 each question', true);
    console.log(raw);
    let data;
  
    try {
      data = JSON.parse(raw);
  
      // If it’s a string after first parse, parse again:
      if (typeof data === 'string') {
        data = JSON.parse(data);
      }
    } catch (e) {
      Logger.log("JSON parse error: " + e);
      return;
    }
  
    Logger.log(data); // check that data is object with questions and types arrays
    if (!data.questions || !Array.isArray(data.questions) || !data.types || !Array.isArray(data.types)) {
        Logger.log("Form data structure invalid");
        return;
      }
    createForm(true, data, true, true);
  }
  
function generateFormQuestions(amount, difficulty, topic, language, questionType, isQuiz) {
  const payload = {
    contents: [
      {
        parts: [
          {
            text: `Generate ${amount} Google Form questions with difficulty level ${difficulty} about "${topic}" in "${language}". 
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
- If isQuiz = ${isQuiz} = true, include an "answers" key in the output.
  - For Multiple Choice, Checkbox, Dropdown, etc: format the answer for the question in the "answers" array as {"Actual Answer": [choice1, choice2, choice3, choice4]}.
  - For grid types (MCG, CG), format the answer for the question in the "answers" array as:
    {
      "row1": ["Answer A", "Answer B"],
      "row2": ["Answer C", "Answer D"]
    }
  - For short/long answer or others without clear choices, you can use simple strings or null.
- If isQuiz = false, do not include the "answers" key at all — just return "questions" and "types", else explicitly include "answers". There should be no null values in the "answers" array.

Only return valid JSON. No comments, no extra text, no markdown.`
          },
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
    payload: JSON.stringify(payload),
  };

  const response = UrlFetchApp.fetch(url, options);
  const data = JSON.parse(response.getContentText());
  const content = data['candidates'][0]['content']['parts'][0]['text'];
  console.log(content);
  return content;
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
  
  function createForm(shuffle, formData, isQuiz, publish) {
    Logger.log("Type of formData: " + typeof formData);
    Logger.log("formData keys: " + Object.keys(formData));
    
    if (!formData || !Array.isArray(formData.questions) || !Array.isArray(formData.types)) {
      throw new Error("Invalid form data structure");
    }
  
    const form = FormApp.create('AI Generated Form');
    form.setIsQuiz(isQuiz);
    form.setShuffleQuestions(shuffle);
  
    const { questions, types, answers = [] } = formData;
  
    for (let i = 0; i < questions.length; i++) {
      const question = questions[i];
      const type = types[i];
      const answer = answers[i];
      let item;
  
      switch (type) {
        case 'MC':
          item = form.addMultipleChoiceItem();
          break;
        case 'SA':
          item = form.addTextItem();
          break;
        case 'LA':
          item = form.addParagraphTextItem();
          break;
        case 'CB':
          item = form.addCheckboxItem();
          break;
        case 'DD':
          item = form.addListItem();
          break;
        case 'LS':
          item = form.addScaleItem().setBounds(1, 5);
          break;
        case 'RT':
          item = form.addScaleItem().setBounds(1, 10);
          break;
        case 'MCG':
          item = form.addGridItem();
          break;
        case 'CG':
          item = form.addCheckboxGridItem();
          break;
        case 'DT':
          item = form.addDateItem();
          break;
        case 'TT':
          item = form.addTimeItem();
          break;
        default:
          item = form.addMultipleChoiceItem();
      }
  
      item.setTitle(question);
  
      // Make required if quiz
      if (isQuiz && typeof item.setRequired === 'function') {
        item.setRequired(true);
      }
  
      // Handle MC/CB/DD
      if (
        answer &&
        typeof answer === 'object' &&
        !Array.isArray(answer) &&
        ['MC', 'CB', 'DD'].includes(type)
      ) {
        const correct = Object.keys(answer)[0];
        const choices = answer[correct];
  
        item.setChoiceValues(choices);
  
        if (isQuiz && type === 'MC' && typeof item.setCorrectAnswer === 'function') {
          item.setCorrectAnswer(correct);
        }
  
        if (type === 'CB') {
          try {
            const validation = FormApp.createCheckboxValidation()
              .setHelpText('Select at least one option.')
              .requireSelectAtLeast(1)
              .build();
            item.setValidation(validation);
          } catch (e) {
            Logger.log('Failed to set CheckboxValidation for question ' + (i + 1) + ': ' + e);
          }
        }
      }
      // Handle MCG, CG grids
      else if (
        answer &&
        typeof answer === 'object' &&
        !Array.isArray(answer) &&
        ['MCG', 'CG'].includes(type)
      ) {
        const rows = Object.keys(answer);
        const colSet = new Set();
  
        rows.forEach(row => {
          if (Array.isArray(answer[row])) {
            answer[row].forEach(col => colSet.add(col));
          }
        });
  
        const columns = Array.from(colSet);
        item.setRows(rows).setColumns(columns);
  
        try {
          if (type === 'MCG') {
            const validation = FormApp.createGridValidation()
              .setHelpText('Please select one option per row.')
              .requireLimitOneResponsePerRow()
              .build();
            item.setValidation(validation);
          } else if (type === 'CG') {
            const validation = FormApp.createCheckboxGridValidation()
              .setHelpText('Please select at least one option per row.')
              .requireLimitOneResponsePerRow()
              .requireSelectAtLeast(1)
              .build();
            item.setValidation(validation);
          }
        } catch (e) {
          Logger.log('Failed to set grid validation for question ' + (i + 1) + ': ' + e);
        }
      }
      // SA regex validation (no ^ and $)
      else if (
        answer &&
        typeof answer === 'string' &&
        type === 'SA'
      ) {
        try {
          const regexPattern = escapeRegExp(answer); // escape any special chars to match literally
          // NO ^ and $ so partial match allowed
          const validation = FormApp.createTextValidation()
            .requireTextMatchesPattern(regexPattern)
            .setHelpText('Your answer must include the correct phrase.')
            .build();
          item.setValidation(validation);
  
          const correctFeedback = FormApp.createFeedback().setText("Correct!").build();
          const incorrectFeedback = FormApp.createFeedback().setText("Incorrect. Try again!").build();
  
          item.setFeedbackForCorrect(correctFeedback);
          item.setFeedbackForIncorrect(incorrectFeedback);
        } catch (e) {
          Logger.log('Failed to set TextValidation for question ' + (i + 1) + ': ' + e);
        }
      }
      // No validation on LA as requested
  
      // Optional: date validation
      if (type === 'DT') {
        try {
          const validation = FormApp.createDateValidation()
            .setHelpText('Please enter a valid date.')
            .requireDateIsValid()
            .build();
          item.setValidation(validation);
        } catch (e) {
          Logger.log('Failed to set DateValidation for question ' + (i + 1) + ': ' + e);
        }
      }
  
      // Optional: time validation
      if (type === 'TT') {
        try {
          const validation = FormApp.createTimeValidation()
            .setHelpText('Please enter a valid time.')
            .requireTimeIsValid()
            .build();
          item.setValidation(validation);
        } catch (e) {
          Logger.log('Failed to set TimeValidation for question ' + (i + 1) + ': ' + e);
        }
      }
    }
  
    form.setPublished(publish);
    Logger.log('Published URL: ' + form.getPublishedUrl());
    Logger.log('Editor URL: ' + form.getEditUrl());
  }
  