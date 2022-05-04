# discord-management-bot

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Feature

### `/mention_to_reaction_users message={message_id} reaction={emoji} ignore_list={True|False}`

メッセージの中で指定した絵文字にリアクションしたユーザーにメンションします

※対象ユーザーは、指定したメッセージがあるチャンネルに存在するユーザー(BOTとメッセージの発言者本人を除く)

| param       | description                | required |
|-------------|----------------------------|----------|
| message     | 対象となるメッセージのID              | must     |
| reaction    | 対象となるリアクションの絵文字            | must     |
| ignore_list | 無視リストを利用するかどうか(デフォルト:True) | optional |

#### examples

- {message_id}のメッセージに😀の絵文字をリアクションしたユーザーにメンションを飛ばす(無視リストを使う)

    ```/mention_to_reaction_users message={message_id} reaction=😀```
- {message_id}のメッセージに:custom_emoji:のカスタム絵文字をリアクションしたユーザーにメンションを飛ばす(無視リストは使わない)

    ```/mention_to_reaction_users message={message_id} reaction=:custom_emoji: ignore_list=False```

- {message_id}のメッセージにリアクションをしていないユーザーにメンションを飛ばす(無視リストを使う)

    ```/mention_to_reaction_users message={message_id} reaction=None```

### `/mention_to_reaction_users manage ignore_list show|download|append={user_id}}remove={user_id}`

コマンドの引数に`manage`を入れると管理モードになります

| param       | description                          | required |
|-------------|--------------------------------------|----------|
| manage      | 管理モードを利用したい場合に指定します                  | must     |
| ignore_list | 無視リストの管理を行います                        | optional |
| show        | 無視リストに登録されているユーザー一覧を返信します            | optional |
| download    | 無視リストに登録されているユーザー一覧をjsonファイルとして投稿します | optional |
| append      | 無視リストにユーザーを追加します                     | optional |
| remove      | 無視リストからユーザーを除外します                    | optional |


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
| after    | この日付より後のメッセージを対象とする     | optional |

### `/download_messages_json channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd}`

指定のチャンネルのメッセージをjsonとして出力します

| param   | description         | required |
|---------|---------------------|----------|
| channel | 対象のチャンネルのID         | must     |
| before  | この日付より前のメッセージを対象とする | optional |
| after   | この日付より後のメッセージを対象とする | optional |
