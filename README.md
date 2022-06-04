# discord-management-bot

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## How to use

1. Discord BOTアカウントを作成する
2. Herokuのアカウントとアプリを作成する
3. GCPのプロジェクトを作り、スプレッドシートにアクセスできるサービスアカウントを作成する
4. 無視リスト用、ボイスチャットログ用のスプレッドシートを用意する
5. HerokuのConfig Varsに後述の環境変数を設定する　
6. HerokuでDeployして起動！

## Environment Variables

利用するためには下記の環境変数の設定が必要です

| name                                   | description                          |
|----------------------------------------|--------------------------------------|
| DISCORD_BOT_TOKEN                      | Discord BOTのトークン                     |
| GOOGLE_CREDENTIALS_FILE                | GCPのサービスアカウント用の認証jsonファイルのパス         |
| IGNORE_LIST_SHEET_ID                   | 無視リスト用のスプレッドシートのID                   |
| LOGGING_VOICE_STATES_SHEET_ID          | ボイスチャット状態ログ用のスプレッドシートのID             |
| LOGGING_VOICE_STATES_WHEN_DATE_CHANGED | ボイスチャット状態ログ用の日付が切り替わるタイミング(HH:MM:SS) |


## Feature

### `/mention_to_reaction_users message={message_id} reaction={emoji} ignore_list={True|False} expand_message={True|False}`

メッセージの中で指定した絵文字にリアクションしたユーザーにメンションします

※対象ユーザーは、指定したメッセージがあるチャンネルに存在するユーザー(BOTとメッセージの発言者本人を除く)

| param          | description       | default | required |
|----------------|-------------------|---------|----------|
| message        | 対象となるメッセージのID     | −       | must     |
| reaction       | 対象となるリアクションの絵文字   | -       | must     |
| ignore_list    | 無視リストを利用するかどうか    | True    | optional |
| expand_message | 対象のメッセージを展開するかどうか | False   | optional |

#### examples

- {message_id}のメッセージに😀の絵文字をリアクションしたユーザーにメンションを飛ばす(無視リストを使う)

    ```/mention_to_reaction_users message={message_id} reaction=😀```
- {message_id}のメッセージに:custom_emoji:のカスタム絵文字をリアクションしたユーザーにメンションを飛ばす(無視リストは使わない)

    ```/mention_to_reaction_users message={message_id} reaction=:custom_emoji: ignore_list=False```

- {message_id}のメッセージにリアクションをしていないユーザー全てにメンションを飛ばす(無視リストを使う)

    ```/mention_to_reaction_users message={message_id} reaction=None```

- {message_id}のメッセージにリアクションをしているユーザー全てにメンションを飛ばす(無視リストを使う)

    ```/mention_to_reaction_users message={message_id} reaction=All```

### `/mention_to_reaction_users manage ignore_list show|download|append={user_id}}|remove={user_id}`

コマンドの引数に`manage`を入れると管理モードになります

| param       | description                          | default | required |
|-------------|--------------------------------------|---------|----------|
| manage      | 管理モードを利用したい場合に指定します                  | パラメータなし | must     |
| ignore_list | 無視リストの管理を行います                        | パラメータなし | optional |
| show        | 無視リストに登録されているユーザー一覧を返信します            | パラメータなし | optional |
| download    | 無視リストに登録されているユーザー一覧をjsonファイルとして投稿します | パラメータなし | optional |
| append      | 無視リストにユーザーを追加します                     | -       | optional |
| remove      | 無視リストからユーザーを除外します                    | -       | optional |

#### examples

- 現在無視リストに登録されているユーザー一覧を表示する
  
    ```/mention_to_reaction_users manage ignore_list show```

- 現在無視リストに登録されているユーザー一覧をjson形式でダウンロードする
  
    ```/mention_to_reaction_users manage ignore_list download```

- 新しく{user_id}を無視リストに追加する
  
    ```/mention_to_reaction_users manage ignore_list append={user_id}```


- 登録されている{user_id}を無視リストから除外する
  
    ```/mention_to_reaction_users manage ignore_list remove={user_id}```
- 
- 無視リストに登録されているユーザーを全解除する
  
    ```/mention_to_reaction_users manage ignore_list remove=all```




### `/message_count channel={channel_id...} before={YYYY-mm-dd} after={YYYY-mm-dd}`

指定のチャンネルで誰が何回発言したのかをまとめてcsv形式にして返します

| param   | description                | default         | required |
|---------|----------------------------|-----------------|----------|
| channel | 対象のチャンネルのID(`,` 区切りで複数指定可) | -               | must     |
| before  | この日付より前のメッセージを対象とする        | None(サーバー開始時から) | optional |
| after   | この日付より後のメッセージを対象とする        | None(現在時刻まで)    | optional |


### `/emoji_count channel={channel_id...} before={YYYY-mm-dd} after={YYYY-mm-dd} order={ascending|descending} rank={1-25} bot={True|False}`

指定のチャンネルでEmojiが何回使われたのかをランキング形式で表示します

| param   | description                                     | default         | required |
|---------|-------------------------------------------------|-----------------|----------|
| channel | 対象のチャンネルのID(`,` 区切りで複数指定可)                      | None(全チャンネル対象)  | optional |
| before  | この日付より前のメッセージを対象とする                             | None(サーバー開始時から) | optional |
| after   | この日付より後のメッセージを対象とする                             | None(現在時刻まで)    | optional |
| order   | ランキングを昇順(ascending)にするか降順(descending)にするか       | ascending(昇順)   | optional |
| rank    | 何位まで表示するか(Discord.Embed.Fieldの表示最大数までしか表示できません) | 10              | optional |
| bot     | BOTが利用したEmojiをカウントするかどうか                        | False           | optional |

### `/download_messages_json channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd}`

指定のチャンネルのメッセージをjsonとして出力します

| param   | description         | default         | required |
|---------|---------------------|-----------------|----------|
| channel | 対象のチャンネルのID         | -               | must     |
| before  | この日付より前のメッセージを対象とする | None(サーバー開始時から) | optional |
| after   | この日付より後のメッセージを対象とする | None(現在時刻まで)    | optional |

### `/logging_voice_states count={state} user={user_id...} channel={channel_id...} before={YYYY-MM-DD} after={YYYY-MM-DD} minimum={True|False}`

BOTを起動すると `discord.py` の `on_voice_state_update` イベントを利用して `LOGGING_VOICE_STATES_SHEET_ID` で指定したスプレッドシートに招待したDiscordサーバーのボイスチャットを監視してログを記録するようになります

このコマンドでは上記で記録したログからボイスチャットのユーザー毎の状態ログを取得します


| param   | description                | default            | required |
|---------|----------------------------|--------------------|----------|
| count   | カウントしたい状態を指定します            | -                  | must     |
| user    | 対象のユーザーのID(`,` 区切りで複数指定可)  | None(サーバー内全ユーザー対象) | optional |
| channel | 対象のチャンネルのID(`,` 区切りで複数指定可) | None(全ボイスチャンネル対象)  | optional |
| before  | この日付より前のメッセージを対象とする        | None(サーバー開始時から)    | optional |
| after   | この日付より後のメッセージを対象とする        | None(現在時刻まで)       | optional |
| minimum | カウントが0の要素を省略します            | True               | optional |

#### 状態一覧

| state        | description     |
|--------------|-----------------|
| join         | ボイスチャンネルに参加した   |
| leave        | ボイスチャンネルから退出した  |
| move         | ボイスチャンネルを移動した   |
| mute_on      | ミュートを有効にした      |
| mute_off     | ミュートを解除した       |
| deaf_on      | スピーカーミュートを有効にした |
| deaf_off     | スピーカーミュートを解除した  |
| stream_begin | 配信を開始した         |
| stream_end   | 配信を終了した         |
| video_on     | WEBカメラを有効にした    |
| video_off    | WEBカメラを解除した     |
| afk_in       | AFKチャンネルに入った    |
| afk_out      | AFKチャンネルから出た    |

### `/notify_when_sent {mode} channel={channel_id}`

指定のチャンネルにメッセージが送信されたときにDMで通知を行います

| param   | description         | default | required             |
|---------|---------------------|---------|----------------------|
| mode    | 利用するモードを指定します※詳細は後述 | -       | must                 |
| channel | 対象のチャンネルのID         | -       | must(モードがlistの場合は不要) |

#### モード一覧

| mode     | description                  |
|----------|------------------------------|
| register | 指定のチャンネルを通知対象として登録します        |
| delete   | 指定のチャンネルの通知対象を解除します          |
| enable   | 指定のチャンネルの通知設定を有効します          |
| disable  | 指定のチャンネルの通知設定を無効します          |
| list     | 現在自身が設定してる通知先のチャンネルの一覧を取得します |

### `/get_system_info`

BOTを実行している環境の情報を取得します  
※開発者がデバッグ用に利用するコマンドです