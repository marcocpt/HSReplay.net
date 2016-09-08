import * as React from "react";
import {GameReplay, CardArtProps, ImageProps, GlobalGamePlayer} from "../interfaces";
import GameHistorySearch from "./GameHistorySearch";
import GameHistoryList from "./GameHistoryList";
import Pager from "./Pager";


interface MyReplaysProps extends ImageProps, CardArtProps, React.ClassAttributes<MyReplays> {
	username: string;
}

interface MyReplaysState {
	working?: boolean;
	query?: string;
	games?: GameReplay[];
	count?: number;
	next?: string,
	previous?: string,
}

export default class MyReplays extends React.Component<MyReplaysProps, MyReplaysState> {

	constructor(props: MyReplaysProps, context: any) {
		super(props, context);
		this.state = {
			working: true,
			query: document.location.hash.substr(1) || "",
			games: [],
			count: 0,
			next: null,
			previous: null,
		};
		this.query("/api/v1/games/");
	}

	protected query(url: string) {
		this.setState({
			working: true,
			games: [],
		});
		$.getJSON(url, {username: this.props.username}, (data) => {
			let games = [];
			if (data.count) {
				games = data.results;
			}
			this.setState({
				working: false,
				games: games,
				count: data.count,
				next: data.next,
				previous: data.previous,
			});
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

		let next = this.state.next && !this.state.working ? () => {
			this.query(this.state.next);
		} : null;

		let previous = this.state.previous && !this.state.working ? () => {
			this.query(this.state.previous);
		} : null;

		return (
			<div>
				<div className="row" id="replay-search">
					<div className="col-md-3 col-sm-4 col-xs-12">
						<GameHistorySearch
							query={this.state.query}
							setQuery={(query: string) => this.setState({query: query})}
						/>
					</div>
					<div className="col-md-9 col-sm-8 col-xs-12 text-right">
						<br className="visible-xs-inline"/>
						<Pager next={next} previous={previous}/>
					</div>
				</div>
				<div className="clearfix"/>
				{content}
				<div className="pull-right">
					<Pager next={next} previous={previous}/>
				</div>
			</div>
		);
	}


}
