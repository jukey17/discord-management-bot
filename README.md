# discord-management-bot

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## 機能

### `/reaction_info message={message_id} bot`

指定のメッセージに誰がどんなリアクションをしたのか、リアクションをしていないのは誰かを返します

| param      | description         | required |
|------------|---------------------|----------|
| message_id | 対象のメッセージのID         | required |
| bot        | BOTを含めるのかどうか        | optional |

### `/message_count channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd}` 

指定のチャンネルで誰が何回発言したのかを返します

| param      | description         | required |
|------------|---------------------|----------|
| channel_id | 対象のチャンネルのID         | required |
| before     | この日付より前のメッセージを対象とする | optional |
| bot        | この日付より後のメッセージを対象とする | optional |
