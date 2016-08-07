import * as React from "react";
import {GameReplay, CardArtProps, ImageProps, GlobalGamePlayer} from "../interfaces";
import GameHistorySearch from "./GameHistorySearch";
import GameHistoryList from "./GameHistoryList";


interface MyReplaysProps extends ImageProps, CardArtProps, React.ClassAttributes<MyReplays> {
}

interface MyReplaysState {
	working?: boolean;
	query?: string;
	games?: GameReplay[];
}

export default class MyReplays extends React.Component<MyReplaysProps, MyReplaysState> {

	constructor(props: MyReplaysProps, context: any) {
		super(props, context);
		this.state = {
			working: true,
			games: [],
			query: document.location.hash.substr(1) || "",
		};
		$.getJSON("/api/v1/games", {username: $("body").data("username")}, (data) => {
			if (data.count) {
				this.setState({
					working: false,
					games: data.results,
				});
			}
		});

	}

	componentDidUpdate(prevProps: MyReplaysProps, prevState: MyReplaysState, prevContext: any): void {
		location.replace("#" + this.state.query);
	}

	render(): JSX.Element {
		let terms = this.state.query.toLowerCase().split(" ").map((word: string) => word.trim()).filter((word: string) => {
			return !!word;
		});
		let games = this.state.games.filter((game: GameReplay): boolean => {
			if (!terms.length) {
				return true;
			}
			let matchingTerms = true;
			terms.forEach((term: string) => {
				let matchingTerm = false;
				game.global_game.players.forEach((player: GlobalGamePlayer): void => {
					let name = player.name.toLowerCase();
					if (name.indexOf(term) !== -1) {
						matchingTerm = true;
					}
					if (term == '"' + name + '"') {
						matchingTerm = true;
					}
				});
				terms.forEach((term: string) => {
					if (+term && game.build == +term) {
						matchingTerm = true;
					}
				});
				if (!matchingTerm) {
					matchingTerms = false;
				}
			});
			return matchingTerms;
		});

		let content = null;
		if (games.length) {
			content =  <GameHistoryList
				image={this.props.image}
				cardArt={this.props.cardArt}
				games={games}
			/>;
		}
		else {
			let message = null;
			if (this.state.working) {
				message = <p>Loading replays…</p>;
			}
			else {
				message = <div>
					<h2>No replay found</h2>
					{!!this.state.query ? <p>
						<a href="#"
						   onClick={(e) => {e.preventDefault(); this.setState({query: ""})}}>Reset search</a>
					</p> : null}
				</div>;
			}
			content = <div className="list-message">{message}</div>;
		}

		return (
			<div>
				<div className="row">
					<div className="col-md-3 col-md-offset-9 col-sm-4 col-sm-offset-8 col-xs-12">
						<GameHistorySearch
							query={this.state.query}
							setQuery={(query: string) => this.setState({query: query})}
						/>
					</div>
				</div>
				<div className="clearfix"/>
				{content}
			</div>
		);
	}


}
