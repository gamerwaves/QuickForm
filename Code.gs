const apiKey = PropertiesService.getScriptProperties().getProperty('genAIKey');

function testRun() {
    const raw = generateFormQuestions(11, 'medium', 'Elon Musk', 'English', 'all types 1 each question', true);
  
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

    // Handle choice-based types
    if (
      answer &&
      typeof answer === 'object' &&
      !Array.isArray(answer) &&
      ['MC', 'CB', 'DD'].includes(type)
    ) {
      const correct = Object.keys(answer)[0];
      const choices = answer[correct];

      item.setChoiceValues(choices);

      if (isQuiz && typeof item.setCorrectAnswer === 'function') {
        item.setCorrectAnswer(correct);
      }
    }

    // Handle grid types
    else if (
      answer &&
      typeof answer === 'object' &&
      !Array.isArray(answer) &&
      ['MCG', 'CG'].includes(type)
    ) {
      const rows = Object.keys(answer);
      const columns = answer[rows[0]];
      item.setRows(rows).setColumns(columns);
      // You can log or store the correct answers separately if needed
    }

    // Handle short/long answer help text
    else if (
      answer &&
      typeof answer === 'string' &&
      ['SA', 'LA'].includes(type)
    ) {
      item.setHelpText('Expected: ' + answer);
    }
  }

  form.setPublished(publish);
  Logger.log('Published URL: ' + form.getPublishedUrl());
  Logger.log('Editor URL: ' + form.getEditUrl());
}
