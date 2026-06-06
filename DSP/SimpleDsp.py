from dataclasses import dataclass
import random
from typing import List, Optional
from RTB_pb2 import BidRequest, BidResponse, SeatBid, Bid

req = BidRequest()

@dataclass
class Campaign:
    id: str
    price: float
    targeting: dict
    creative: str
    budget: float

class SimpleDSP:
    def __init__(self):
        # Initialize with some sample campaigns
        self.campaigns = [
            Campaign(
                id="camp1",
                price=1.5,
                targeting={"country": ["US", "UK"], "banner_sizes": [(300, 250)]},
                creative="<ad>Creative 1</ad>",
                budget=1000.0
            ),
            Campaign(
                id="camp2",
                price=2.0,
                targeting={"country": ["US"], "banner_sizes": [(728, 90)]},
                creative="<ad>Creative 2</ad>",
                budget=2000.0
            )
        ]

    def process_bid_request(self, request: BidRequest) -> Optional[BidResponse]:
        try:
            # 1. Basic validation
            if not self._validate_request(request):
                return None

            # 2. Find eligible campaigns
            eligible_campaigns = self._filter_campaigns(request)
            if not eligible_campaigns:
                return None

            # 3. Select best campaign and generate bid
            selected_campaign = self._select_campaign(eligible_campaigns, request)
            if not selected_campaign:
                return None

            # 4. Create bid response
            return self._create_bid_response(request, selected_campaign)

        except Exception as e:
            print(f"Error processing bid request: {e}")
            return None

    def _validate_request(self, request) -> bool:
        return bool(request.id and request.imp)

    def _filter_campaigns(self, request) -> List[Campaign]:
        eligible_campaigns = []
        
        for campaign in self.campaigns:
            if campaign.budget <= 0:
                continue

            # Check geo targeting
            if request.user and request.user.geo:
                if request.user.geo.country not in campaign.targeting["country"]:
                    continue

            # Check banner sizes
            for imp in request.imp:
                if imp.banner:
                    banner_sizes = list(zip(imp.banner.w, imp.banner.h))
                    if not any(size in campaign.targeting["banner_sizes"] for size in banner_sizes):
                        continue

            eligible_campaigns.append(campaign)

        return eligible_campaigns

    def _select_campaign(self, campaigns: List[Campaign], request) -> Optional[Campaign]:
        # Simple selection - choose random campaign
        return random.choice(campaigns) if campaigns else None

    def _create_bid_response(self, request, campaign: Campaign):
        response = BidResponse()
        response.id = request.id
        response.currency = "USD"

        seatbid = SeatBid()
        bid = Bid()
        bid.id = f"bid_{random.randint(1000, 9999)}"
        bid.impid = request.imp[0].id
        bid.price = campaign.price
        bid.adid = campaign.id
        bid.adm = campaign.creative
        bid.nurl = f"http://47.236.3.20/win?auction_id={bid.id}"

        seatbid.bid.append(bid)
        response.seatbid.append(seatbid)

        return response
