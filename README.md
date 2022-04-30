# discord-management-bot

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## 機能

### `/reaction_info message={message_id} bot`

指定のメッセージに誰がどんなリアクションをしたのか、リアクションをしていないのは誰かを返します

| param   | description         | required |
|---------|---------------------|----------|
| message | 対象のメッセージのID         | must     |
| bot     | BOTを含めるのかどうか        | optional |

### `/message_count channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd}`

指定のチャンネルで誰が何回発言したのかをまとめてcsv形式にして返します

| param   | description         | required |
|---------|---------------------|----------|
| channel | 対象のチャンネルのID         | must     |
| before  | この日付より前のメッセージを対象とする | optional |
| bot     | この日付より後のメッセージを対象とする | optional |

### `/message_count channels={channel_id0, channelid1, channel_id2...} before={YYYY-mm-dd} after={YYYY-mm-dd}`

指定のチャンネル(複数)で誰が何回発言したのかをまとめてcsv形式にして返します

| param    | description             | required |
|----------|-------------------------|----------|
| channels | 対象のチャンネルのIDをカンマ区切りで複数指定 | must     |
| before   | この日付より前のメッセージを対象とする     | optional |
| bot      | この日付より後のメッセージを対象とする     | optional |

### `/download_messages_json channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd}`

指定のチャンネルのメッセージをjsonとして出力します

| param   | description         | required |
|---------|---------------------|----------|
| channel | 対象のチャンネルのID         | must     |
| before  | この日付より前のメッセージを対象とする | optional |
| bot     | この日付より後のメッセージを対象とする | optional |
