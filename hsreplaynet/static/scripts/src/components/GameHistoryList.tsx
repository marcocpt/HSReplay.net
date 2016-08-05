import * as React from "react";
import GameHistoryItem from "./GameHistoryItem";
import {GameReplay, CardArtProps, ImageProps, GlobalGamePlayer} from "../interfaces";
import GameHistorySearch from "./GameHistorySearch";


interface GameHistoryListProps extends ImageProps, CardArtProps, React.ClassAttributes<GameHistoryList> {
	games: GameReplay[];
}

interface GameHistoryListState {
	query?: string;
}

export default class GameHistoryList extends React.Component<GameHistoryListProps, GameHistoryListState> {

	constructor(props: GameHistoryListProps, context: any) {
		super(props, context);
		this.state = {
			query: document.location.hash.substr(1) || "",
		}
	}

	componentDidUpdate(prevProps: GameHistoryListProps, prevState: GameHistoryListState, prevContext: any): void {
		location.replace("#" + this.state.query);
	}

	render(): JSX.Element {
		let columns = [];
		let terms = this.state.query.toLowerCase().split(" ").map((word: string) => word.trim()).filter((word: string) => {
			return !!word;
		});
		this.props.games.filter((game: GameReplay): boolean => {
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
		}).forEach((game: GameReplay, i: number) => {
			var startTime: Date = new Date(game.global_game.match_start);
			var endTime: Date = new Date(game.global_game.match_end);
			if (i > 0) {
				if (!(i % 2)) {
					columns.push(<div className="clearfix visible-sm-block"></div>);
				}
				if (!(i % 3)) {
					columns.push(<div className="clearfix visible-md-block"></div>);
				}
				if (!(i % 4)) {
					columns.push(<div className="clearfix visible-lg-block"></div>);
				}
			}
			columns.push(
				<GameHistoryItem
					key={i}
					cardArt={this.props.cardArt}
					image={this.props.image}
					shortid={game.shortid}
					players={game.global_game.players}
					startTime={startTime}
					endTime={endTime}
					gameType={game.global_game.game_type}
					disconnected={game.disconnected}
					turns={game.global_game.num_turns}
					won={game.won}
				/>
			);
		});
		return (
			<div className="row">
				<div className="col-lg-12" id="replay-filter">
					<GameHistorySearch
						query={this.state.query}
						setQuery={(query: string) => this.setState({query: query})}
					/>
				</div>
				<div className="col-lg-12">
					<div className="row">
						{columns.length ? columns :
							<div className="col-lg-12 list-message">
								<h2>No replay found</h2>
								<p>
									<a href="#" onClick={(e) => {e.preventDefault(); this.setState({query: ""})}}>Reset search</a>
								</p>
							</div>}
					</div>
				</div>
			</div>
		);
	}
}
