# discord-management-bot

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Installation

準備中

## Quick start

準備中

## Features

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

- XXXXのメッセージに😀の絵文字をリアクションしたユーザーにメンションを飛ばす(無視リストを使う)

  ```/mention_to_reaction_users message=XXXX reaction=😀```
- XXXXのメッセージに:custom_emoji:のカスタム絵文字をリアクションしたユーザーにメンションを飛ばす(無視リストは使わない)

  ```/mention_to_reaction_users message=XXXX reaction=:custom_emoji: ignore_list=False```

- XXXXのメッセージにリアクションをしていないユーザー全てにメンションを飛ばす(無視リストを使う)

  ```/mention_to_reaction_users message=XXXX reaction=None```

- XXXXのメッセージにリアクションをしているユーザー全てにメンションを飛ばしてメッセージを展開する(無視リストを使う)

  ```/mention_to_reaction_users message=XXXX reaction=All expand_message=True```

---

### `/mention_to_reaction_users manage {mode} {options}`

`mention_to_reaction_users` コマンドの引数に`manage`を入れると管理モードになります

#### mode 一覧

| mode        | description   |
|-------------|---------------|
| ignore_list | 無視リストの管理を行います |

#### ignore_list options 一覧

| options  | description                          | params    | required |
|----------|--------------------------------------|-----------|----------|
| show     | 無視リストに登録されているユーザー一覧を返信します            | パラメータなし   | -        |
| download | 無視リストに登録されているユーザー一覧をjsonファイルとして投稿します | パラメータなし   | -        |
| append   | 無視リストにユーザーを追加します                     | {user_id} | must     |
| remove   | 無視リストからユーザーを除外します                    | {user_id} | must     |

#### examples

- 現在無視リストに登録されているユーザー一覧を表示する

  ```/mention_to_reaction_users manage ignore_list show```

- 現在無視リストに登録されているユーザー一覧をjson形式でダウンロードする

  ```/mention_to_reaction_users manage ignore_list download```

- 新しくXXXXを無視リストに追加する

  ```/mention_to_reaction_users manage ignore_list append=XXXX```

- 登録されているXXXXを無視リストから除外する

  ```/mention_to_reaction_users manage ignore_list remove=XXXX```

- 無視リストに登録されているユーザーを全解除する

  ```/mention_to_reaction_users manage ignore_list remove=all```

----

### `/message_count channel={channel_id...} before={YYYY-mm-dd} after={YYYY-mm-dd}`

指定のチャンネルでサーバー内の各ユーザーが何回発言したのかをまとめてcsv形式にして返します

| param   | description                | default         | required |
|---------|----------------------------|-----------------|----------|
| channel | 対象のチャンネルのID(`,` 区切りで複数指定可) | -               | must     |
| before  | この日付より前のメッセージを対象とする        | None(サーバー開始時から) | optional |
| after   | この日付より後のメッセージを対象とする        | None(現在時刻まで)    | optional |

#### examples

- XXXXのチャンネルの全期間でサーバー内の各ユーザーが何回発言したのかをcsv形式にして取得する

  ```/message_count channel=XXXX```

- XXXXとYYYYのチャンネルにおいて2022/01/01~2022/01/31の期間を対象にサーバー内の各ユーザーが何回発言したのかをcsv形式にして取得する

  ```/message_count channel=XXXX,YYYY after=2022/01/01 before=2022/01/31```

----

### `/emoji_ranking channel={channel_id...} before={YYYY-mm-dd} after={YYYY-mm-dd} order={ascending|descending} rank={1-25} bot={True|False}`

指定のチャンネルでカスタム絵文字が何回使われたかをランキング形式にして返します

| param   | description                | default         | required |
|---------|----------------------------|-----------------|----------|
| channel | 対象のチャンネルのID(`,` 区切りで複数指定可) | None(全てのチャンネル)  | optional |
| before  | この日付より前のメッセージを対象とする        | None(サーバー開始時から) | optional |
| after   | この日付より後のメッセージを対象とする        | None(現在時刻まで)    | optional |
| order   | ランキングのソート方法 (昇順または降順)      | ascending       | optional |
| rank    | 表示するランキング数 (1-25)          | 10              | optional |
| bot     | BOTによるメッセージとリアクションを含むかどうか  | False           | optional |

#### examples

- 全てのチャンネルの全期間におけるカスタム絵文字の使用数ランキングワースト10を表示する

  ```/emoji_ranking```

- XXXXのチャンネルの全期間におけるカスタム絵文字の使用数ランキングTOP10を表示する

  ```/emoji_ranking channel=XXXX order=descending```

- XXXXとYYYYとZZZZのチャンネルにおいて2022/01/01~2022/01/31の期間を対象としたカスタム絵文字の使用数ランキングTOP5を表示する(BOTによる使用も含む)

  ```/emoji_ranking channel=XXXX,YYYY,ZZZZ, order=descending rank=5 bot```

see also, https://github.com/jukey17/discord-emoji-ranking/

----

### `/download_messages_json channel={channel_id} before={YYYY-mm-dd} after={YYYY-mm-dd}`

指定のチャンネルのメッセージをjsonとして出力します

| param   | description         | default         | required |
|---------|---------------------|-----------------|----------|
| channel | 対象のチャンネルのID         | -               | must     |
| before  | この日付より前のメッセージを対象とする | None(サーバー開始時から) | optional |
| after   | この日付より後のメッセージを対象とする | None(現在時刻まで)    | optional |

----

### `/logging_voice_states count={state} user={user_id...} channel={channel_id...} before={YYYY-MM-DD} after={YYYY-MM-DD} minimum={True|False}`

BOTを起動すると `discord.py` の `on_voice_state_update` イベントを利用して `LOGGING_VOICE_STATES_SHEET_ID`
で指定したスプレッドシートに招待したDiscordサーバーのボイスチャットを監視してログを記録するようになります

このコマンドでは上記で記録したログからボイスチャットのユーザー毎の状態ログを取得します

| param   | description                | default            | required |
|---------|----------------------------|--------------------|----------|
| count   | カウントしたい状態を指定します            | -                  | must     |
| user    | 対象のユーザーのID(`,` 区切りで複数指定可)  | None(サーバー内全ユーザー対象) | optional |
| channel | 対象のチャンネルのID(`,` 区切りで複数指定可) | None(全ボイスチャンネル対象)  | optional |
| before  | この日付より前のメッセージを対象とする        | None(サーバー開始時から)    | optional |
| after   | この日付より後のメッセージを対象とする        | None(現在時刻まで)       | optional |
| minimum | カウントが0の要素を省略します            | True               | optional |

#### state 一覧

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

----

### `/notify_when_sent {mode} channel={channel_id}`

指定のチャンネルにメッセージが送信されたときにDMで通知を行います

| param   | description   | default | required             |
|---------|---------------|---------|----------------------|
| mode    | 利用するモードを指定します | -       | must                 |
| channel | 対象のチャンネルのID   | -       | must(モードがlistの場合は不要) |

#### mode 一覧

| mode     | description                  |
|----------|------------------------------|
| register | 指定のチャンネルを通知対象として登録します        |
| delete   | 指定のチャンネルの通知対象を解除します          |
| enable   | 指定のチャンネルの通知設定を有効します          |
| disable  | 指定のチャンネルの通知設定を無効します          |
| list     | 現在自身が設定してる通知先のチャンネルの一覧を取得します |

----

### `/get_system_info`

BOTを実行している環境の情報を取得します  
※開発者がデバッグ用に利用するコマンドです