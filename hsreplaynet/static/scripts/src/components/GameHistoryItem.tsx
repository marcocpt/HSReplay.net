import * as React from "react";
import {GlobalGamePlayer, ImageProps, CardArtProps} from "../interfaces";
import GameHistoryPlayer from "./GameHistoryPlayer";
import {PlayState, BnetGameType} from "../hearthstone";


interface GameHistoryItemProps extends ImageProps, CardArtProps, React.ClassAttributes<GameHistoryItem> {
	shortid: string;
	players: GlobalGamePlayer[];
	startTime: Date;
	endTime: Date;
	gameType: number;
	disconnected: boolean;
	turns: number;
	won: boolean;
}

interface GameHistoryItemState {
}

function humanTime(seconds) {
	// TODO: use something better
	var days = Math.floor((seconds % 31536000) / 86400);
	var hours = Math.floor(((seconds % 31536000) % 86400) / 3600);
	var mins = Math.floor((((seconds % 31536000) % 86400) % 3600) / 60);
	if (days) {
		return days + " days";
	}
	if (hours) {
		return hours + " hours";
	}
	return mins + " minutes";
}

export default class GameHistoryItem extends React.Component<GameHistoryItemProps, GameHistoryItemState> {
	constructor(props: GameHistoryItemProps, context: any) {
		super(props, context);
	}

	getDuration(): string {
		var seconds = this.props.endTime.getTime() - this.props.startTime.getTime();
		return humanTime(seconds / 1000);
	}

	getPlayedTime(): string {
		var seconds = new Date().getTime() - this.props.endTime.getTime();
		return humanTime(seconds / 1000) + " ago";
	}

	getIcon(): JSX.Element {
		if (this.props.disconnected) {
			return <img src={STATIC_URL + "images/dc.png"} className="hsreplay-type" alt="Disconnected"/>;
		}
		if (this.props.gameType == BnetGameType.BGT_ARENA) {
			return <img src={STATIC_URL + "images/arena-medals/Medal_Key_2.png"} className="hsreplay-type" alt="Arena"/>;
		}
		if (this.props.gameType == 16) {
			return <img src={STATIC_URL + "images/brawl.png"} className="hsreplay-type" alt="Tavern Brawl"/>;
		}
		return null;
	}

	render(): JSX.Element {
		return (<div className="col-xs-12 col-sm-6 col-md-4 col-lg-3 game-history-item">
			<a href={"/replay/" + this.props.shortid} className={this.props.won ? "won" : "lost"}>
				<div className="hsreplay-involved">
					<img src={this.props.image("vs.png")} className="hsreplay-versus"/>
					{this.props.players.map((player: GlobalGamePlayer, i: number) => {
						return <GameHistoryPlayer
							cardArt={this.props.cardArt}
							name={player.name}
							heroId={player.hero_id}
							won={player.final_state == PlayState.WON}
						/>;
					})}
				</div>
				<div className="hsreplay-details">
					<dl>
						<dt>Played</dt>
						<dd>{this.getPlayedTime()}</dd>
						<dt>Duration</dt>
						<dd>{this.getDuration()}</dd>
						<dt>Turns</dt>
						<dd>{Math.floor(this.props.turns / 2)} turns</dd>
					</dl><div>
						{this.getIcon()}
					</div>
				</div>
			</a>
		</div>);
	}
}
